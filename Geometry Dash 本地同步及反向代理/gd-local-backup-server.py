#!/usr/bin/python3
import asyncio
import base64
import json
import os
import time
from collections import defaultdict
from enum import Enum
from types import TracebackType
from typing import (Annotated, Any, AsyncContextManager, AsyncGenerator,
                    Awaitable, ClassVar, Generator, Literal)
from urllib.parse import quote as encodeuri
from urllib.parse import unquote as decodeuri

import aiohttp
from aiohttp import web
from loguru import logger
from pydantic import (AnyUrl, BaseModel, Field, HttpUrl, IPvAnyAddress,
                      NonNegativeFloat, NonNegativeInt, StringConstraints,
                      TypeAdapter)
from pydantic_core import to_jsonable_python

Gjp2Str = Annotated[str, StringConstraints(to_lower=True, pattern="^[0-9a-f]{40}$")]
OFFICIAL_SERVER = "https://www.boomlings.com/database"


def pydantic_dump(*args: Any, **kw: Any) -> None:
    json.dump(*args, separators=(",", ":"), default=to_jsonable_python, **kw)


def try_scandir(path: str) -> Generator[os.DirEntry[str], Any, Any]:
    try:
        yield from os.scandir(path)
    except FileNotFoundError:
        pass


def try_remove(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


class Gjp2Mode(Enum):
    AUTO = "auto"
    IGNORE = "ignore"


class Auth(BaseModel):
    fetch_gjp2: bool = True
    gjp2_override: dict[int, Gjp2Str | Gjp2Mode] = Field(default_factory=dict)

    def write_gjp2(self, account_id: int, gjp2: Gjp2Str) -> None:
        if not self.has_account(account_id):
            return
        if account_id in self.gjp2_override:
            fetch_gjp2 = self.gjp2_override[account_id] == Gjp2Mode.AUTO
        else:
            fetch_gjp2 = self.fetch_gjp2
        if fetch_gjp2:
            os.makedirs(str(account_id), exist_ok=True)
            with open(f"accounts/{account_id}/gjp2.txt", "w") as f:
                f.write(gjp2)

    def validate_gjp2(self, account_id: int, gjp2: Gjp2Str) -> bool:
        if not self.has_account(account_id):
            return False
        account_gjp2 = self.gjp2_override.get(account_id, Gjp2Mode.AUTO if self.fetch_gjp2 else Gjp2Mode.IGNORE)
        if account_gjp2 == Gjp2Mode.IGNORE:
            return True
        if account_gjp2 == Gjp2Mode.AUTO:
            try:
                with open(f"accounts/{account_id}/gjp2.txt") as f:
                    account_gjp2 = f.readline().rstrip()
            except FileNotFoundError:
                return False
        return gjp2 == account_gjp2

    def has_account(self, account_id: int) -> bool:
        return True


class BlacklistAuth(Auth):
    type: Literal["blacklist"]
    blacklist: set[int] = Field(default_factory=set)

    def has_account(self, account_id: int) -> bool:
        return account_id not in self.blacklist


class WhitelistAuth(Auth):
    type: Literal["whitelist"]
    whitelist: set[int] = Field(default_factory=set)

    def has_account(self, account_id: int) -> bool:
        return account_id in self.whitelist


class Config(BaseModel):
    host: IPvAnyAddress = Field(default="0.0.0.0")
    port: int = Field(default=80, ge=0, lt=65536)
    game_server: HttpUrl = Field(default=OFFICIAL_SERVER)
    game_retry_count: None | NonNegativeInt = 4
    game_retry_4xx: bool = False
    game_proxy: None | HttpUrl = None
    backup_enabled: bool | Literal["local"] = True
    backup_server: None | HttpUrl = None
    backup_retry_count: None | NonNegativeInt = None
    backup_retry_interval: NonNegativeFloat = 60
    backup_retry_4xx: bool = False
    backup_proxy: None | HttpUrl = None
    backup_auth: BlacklistAuth | WhitelistAuth = Field(default_factory=lambda: BlacklistAuth(type="blacklist"))
    song_enabled: bool = True
    song_ngproxy: bool = True
    song_bypass_ngproxy: bool = True
    song_retry_count: None | NonNegativeInt = 4
    song_retry_4xx: bool = False
    song_proxy: None | HttpUrl = None
    song_info_ttl: None | NonNegativeFloat = 600
    assets_enabled: bool = True
    assets_server: None | HttpUrl = None
    assets_retry_count: None | NonNegativeInt = 4
    assets_retry_4xx: bool = False
    assets_proxy: None | HttpUrl = None
    assets_server_ttl: None | NonNegativeFloat = 600
    prefetch: bool = True
    prefetch_ttl: None | NonNegativeFloat = 600
    prefetch_target_dir: None | str = None

    @property
    def backup_server_repr(self) -> str:
        server = "从游戏服务器获取" if not self.backup_server else str(self.backup_server)
        if not self.backup_enabled:
            return f"{server}（已禁用本地备份）"
        elif self.backup_enabled == "local":
            return f"{server}（已禁用上传）"
        return server

    @property
    def game_proxy_str(self) -> str | None:
        return None if self.game_proxy is None else str(self.game_proxy)

    @property
    def backup_proxy_str(self) -> str | None:
        return None if self.backup_proxy is None else str(self.backup_proxy)

    @property
    def song_proxy_str(self) -> str | None:
        return None if self.song_proxy is None else str(self.song_proxy)

    @property
    def assets_proxy_str(self) -> str | None:
        return None if self.assets_proxy is None else str(self.assets_proxy)


class BackupTask(BaseModel):
    time: float = Field(default_factory=time.time)
    server: HttpUrl
    token: dict[str, str]
    retry_left: NonNegativeInt | None

    @property
    def server_str(self) -> str:
        return str(self.server).removesuffix("/")


class BackupScheduler:
    def __init__(self, client: aiohttp.ClientSession, retry_interval: float = 60, retry_4xx: bool = False, **kw: Any) -> None:
        self.tasks: dict[int, BackupTask] = {}
        self.locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.handles: dict[int, asyncio.TimerHandle] = {}
        client.cookie_jar.update_cookies({"gd": "1"})
        self.client = client
        self.retry_interval = retry_interval
        self.retry_4xx = retry_4xx
        self.kw = kw

    def schedule(self, account_id: int, task: BackupTask, delay: float = 0) -> None:
        def do_scheduled_upload() -> None:
            del self.handles[account_id]
            asyncio.create_task(self.do_upload(account_id, self.tasks.pop(account_id)))

        if account_id in self.tasks and task.time < self.tasks[account_id].time:
            return
        self.tasks[account_id] = task

        loop = asyncio.get_running_loop()
        if account_id in self.handles and (handle := self.handles[account_id]).when() - loop.time() > delay:
            handle.cancel()
            del self.handles[account_id]
        if account_id not in self.handles:
            self.handles[account_id] = loop.call_later(delay, do_scheduled_upload)

    async def do_upload(self, account_id: int, task: BackupTask) -> None:
        async with self.locks[account_id]:
            logger.info(f"正在备份 {account_id} 的数据到服务器 {task.server}")
            with open(f"accounts/{account_id}/CCGameManager.xml.gz", "rb") as f:
                ccgamemanager = base64.urlsafe_b64encode(f.read()).decode()
            with open(f"accounts/{account_id}/CCLocalLevels.xml.gz", "rb") as f:
                cclocallevels = base64.urlsafe_b64encode(f.read()).decode()
            form = {"accountID": account_id, "saveData": f"{ccgamemanager};{cclocallevels}", **task.token}
            async with self.client.post(f"{task.server_str}/database/accounts/backupGJAccountNew.php", data=form, **self.kw) as response:
                result = await response.read()
                if response.ok and result == b"1":
                    logger.success(f"备份 {account_id} 的数据成功")
                    return
                if task.retry_left != 0 and (self.retry_4xx or not 400 <= response.status <= 499):
                    logger.warning(f"备份 {account_id} 的数据失败，响应: {result!r}，剩余 {task.retry_left} 次重试，下一次在 {self.retry_interval} 秒后")
                    task.retry_left = None if task.retry_left is None else task.retry_left - 1
                    self.schedule(account_id, task, self.retry_interval)
                else:
                    logger.warning(f"备份 {account_id} 的数据失败，响应: {result!r}")


async def stream_response(request: web.BaseRequest, response: aiohttp.ClientResponse) -> web.StreamResponse:
    headers = {}
    if "Content-Length" in response.headers:
        headers["Content-Length"] = response.headers["Content-Length"]
    stream = web.StreamResponse(status=response.status, headers=headers)
    await stream.prepare(request)
    data, _ = await response.content.readchunk()
    while data:
        await stream.write(data)
        data, _ = await response.content.readchunk()
    await stream.write_eof()
    return stream


async def api_read(response: aiohttp.ClientResponse) -> str | web.Response:
    text = await response.text(errors="replace")
    if not text or not response.ok:
        return web.Response(status=response.status, body=text)
    try:
        return web.Response(status=response.status, body=str(int(text)))
    except ValueError:
        pass
    return text


class ApiManager:
    def __init__(self, client: aiohttp.ClientSession, server: str, retry_count: int | None = None, retry_4xx: bool = False, **kw: Any) -> None:
        client.cookie_jar.update_cookies({"gd": "1"})
        self.client = client
        self.server = server
        self.retry_count = retry_count
        self.retry_4xx = retry_4xx
        self.kw = kw

    def __getitem__(self, api: str) -> "ApiCaller":
        return ApiCaller(self, api)

    def __getattr__(self, api: str) -> "ApiCaller":
        return ApiCaller(self, api)


class ApiCaller:
    def __init__(self, manager: ApiManager, api: str) -> None:
        self.manager = manager
        self.api = api

    def __call__(self, request: web.BaseRequest | None = None, **kw: Any) -> "ApiContextManager":
        return ApiContextManager(self.manager, self.api, request, **kw)

    async def stream(self, request: web.BaseRequest, **kw: Any) -> web.StreamResponse:
        async with self(request, **kw) as response:
            return await stream_response(request, response)


class ApiContextManager(AsyncContextManager, Awaitable[aiohttp.ClientResponse]):
    def __init__(self, manager: ApiManager, api: str, request: web.BaseRequest | None, **kw: Any) -> None:
        self.manager = manager
        self.api = api
        self.request = request
        self.kw = kw

    def __await__(self) -> Generator[Any, Any, aiohttp.ClientResponse]:
        return self.__aenter__().__await__()

    async def __aenter__(self) -> aiohttp.ClientResponse:
        kw = self.manager.kw.copy()
        if self.request:
            kw["data"] = await self.request.read()
            kw["headers"] = {"Content-Type": self.request.headers["Content-Type"]}
        kw.update(self.kw)
        retry_left = self.manager.retry_count
        while True:
            response = await self.manager.client.post(f"{self.manager.server}/{self.api}.php", **kw)
            if response.ok or (retry_left is not None and retry_left <= 0) or (400 <= response.status <= 499 and not self.manager.retry_4xx):
                logger.log("DEBUG" if response.ok else "WARNING", f"{response.status} {response.method} {response.url}")
                self._resp = response
                return response
            logger.warning(f"{response.status} {response.method} {response.url} 剩余 {retry_left} 次重试")
            retry_left = None if retry_left is None else retry_left - 1
            await response.__aexit__(None, None, None)

    async def __aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        await self._resp.__aexit__(exc_type, exc, tb)


class SongInfo(BaseModel):
    time: float = Field(default_factory=time.time)
    data: dict[int, str] | int

    @staticmethod
    def load(info: str) -> dict[int, str]:
        data = info.split("~|~")
        data = {int(data[i]): data[i + 1] for i in range(0, len(data), 2)}
        if 10 in data:
            data[10] = decodeuri(data[10])
        return data

    @staticmethod
    def dump(data: dict[int, str]) -> str:
        return "~|~".join(f"{k}~|~{encodeuri(v, safe='') if k == 10 else v}" for k, v in data.items())


class SongInfoCache:
    def __init__(self, api: ApiCaller, ttl: float | None) -> None:
        self.api = api
        self.ttl = ttl
        self.delete_tokens: dict[int, asyncio.TimerHandle] = {}

    async def get(self, id: int) -> dict[int, str] | int:
        try:
            with open(f"song_infos/{id}.json", "r") as f:
                cache = SongInfo.model_validate(json.load(f))
            if self.ttl is None or time.time() - cache.time < self.ttl:
                return cache.data
            logger.info(f"歌曲 {id} 的元数据缓存已过期，重新获取中")
        except FileNotFoundError:
            pass
        async with self.api(data={"songID": id, "secret": "Wmfd2893gb7"}) as response:
            info = await response.text(errors="replace")
            if not response.ok or not info:
                try:
                    return int(info)
                except ValueError:
                    return -1
            try:
                info = int(info)
            except ValueError:
                info = SongInfo.load(info)
        self.insert(id, info)
        return info

    def insert(self, id: int, info: dict[int, str] | int) -> None:
        os.makedirs("song_infos", exist_ok=True)
        with open(f"song_infos/{id}.json", "w") as f:
            logger.info(f"已创建歌曲 {id} 的元数据缓存")
            pydantic_dump(SongInfo(data=info), f)
            if self.ttl is not None:
                self.schedule_delete(id, self.ttl)

    def schedule_delete(self, id: int, delay: float) -> None:
        def do_delete() -> None:
            logger.info(f"已删除歌曲 {id} 的元数据缓存")
            os.remove(f"song_infos/{id}.json")
            self.delete_tokens.pop(id, None)

        if token := self.delete_tokens.pop(id, None):
            token.cancel()
        if delay <= 0:
            do_delete()
        else:
            self.delete_tokens[id] = asyncio.get_running_loop().call_later(delay, do_delete)

    def clean(self) -> None:
        if self.ttl is None:
            return
        current_time = time.time()
        for file in try_scandir("song_infos"):
            with open(file.path) as f:
                cache = SongInfo.model_validate(json.load(f))
                id = int(file.name.removesuffix(".json"))
                self.schedule_delete(id, self.ttl - (current_time - cache.time))


class AssetsServer:
    async def __call__(self) -> str:
        raise NotImplementedError


class AssetsServerInfo(BaseModel):
    time: float = Field(default_factory=time.time)
    cdn: str


class AssetsServerCached(AssetsServer):
    def __init__(self, api: ApiCaller, ttl: float | None = 600) -> None:
        self.api = api
        self.ttl = ttl
        self.lock = asyncio.Lock()

    async def __call__(self) -> str:
        async with self.lock:
            try:
                with open("assets_server.json", "r") as f:
                    cache = AssetsServerInfo.model_validate(json.load(f))
                if self.ttl is None or time.time() - cache.time < self.ttl:
                    return cache.cdn
            except FileNotFoundError:
                pass
            async with self.api() as response:
                cdn = await api_read(response)
            if isinstance(cdn, web.Response):
                return ""
            with open("assets_server.json", "w") as f:
                pydantic_dump(AssetsServerInfo(cdn=cdn), f)
            return cdn


class AssetsServerStatic(AssetsServer):
    def __init__(self, server: str) -> None:
        self.server = server

    async def __call__(self) -> str:
        return self.server


class PrefetchInfo(BaseModel):
    time: float = Field(default_factory=time.time)
    error: str | None = None


class PrefetchTask:
    def __init__(self, prefetcher: "Prefetcher", id: int) -> None:
        self.prefetcher = prefetcher
        self.id = id
        self.prepare_future: asyncio.Future[str | tuple[int, str]] = asyncio.Future()
        self.chunk_events: set[asyncio.Event] = set()
        self.finished = False
        logger.info(f"开始下载 {self.prefetcher.DIR} {id}")
        asyncio.create_task(self.download())

    async def download(self) -> None:
        try:
            try_remove(f"{self.prefetcher.DIR}/{self.id}.json")
            try_remove(f"{self.prefetcher.DIR}/{self.id}")
            response = await self.prefetcher.request(self.id)
            os.makedirs(self.prefetcher.DIR, exist_ok=True)
            if isinstance(response, str):
                with open(f"{self.prefetcher.DIR}/{self.id}.json") as f:
                    pydantic_dump(PrefetchInfo(error=response), f)
                self.prepare_future.set_result((404, response))
                return
            async with response:
                if not response.ok:
                    self.prepare_future.set_result((response.status, await response.text()))
                    return
                with open(f"{self.prefetcher.DIR}/{self.id}", "wb") as f:
                    self.prepare_future.set_result(response.headers["Content-Length"])
                    data, _ = await response.content.readchunk()
                    while data:
                        f.write(data)
                        for event in self.chunk_events:
                            event.set()
                        data, _ = await response.content.readchunk()
            logger.info(f"下载完成 {self.prefetcher.DIR} {self.id}")
            with open(f"{self.prefetcher.DIR}/{self.id}.json", "w") as f:
                pydantic_dump(PrefetchInfo(), f)
        finally:
            self.finished = True
            if self.prefetcher.tasks.get(self.id) == self:
                del self.prefetcher.tasks[self.id]
            if self.prefetcher.ttl is not None:
                self.prefetcher.schedule_delete(self.id, self.prefetcher.ttl)

    async def stream(self, request: web.Request) -> web.StreamResponse:
        logger.info(f"正在串流 {self.prefetcher.DIR} {self.id}")
        size = await self.prepare_future
        if isinstance(size, tuple):
            return web.Response(body=size[1], status=size[0])
        response = web.StreamResponse(headers={"Content-Length": size})
        await response.prepare(request)
        chunk_event = asyncio.Event()
        self.chunk_events.add(chunk_event)
        try:
            with open(f"{self.prefetcher.DIR}/{self.id}", "rb") as f:
                await response.write(f.read())
                while not self.finished:
                    await chunk_event.wait()
                    chunk_event.clear()
                    await response.write(f.read())
        finally:
            self.chunk_events.remove(chunk_event)
        return response


class Prefetcher:
    DIR: ClassVar[str]

    def __init__(self, ttl: float | None) -> None:
        self.tasks: dict[int, PrefetchTask] = {}
        self.ttl = ttl
        self.delete_tokens: dict[int, asyncio.TimerHandle] = {}

    async def request(self, id: int) -> aiohttp.ClientResponse | str:
        raise NotImplementedError

    def schedule(self, id: int) -> PrefetchTask:
        try:
            return self.tasks[id]
        except KeyError:
            task = self.tasks[id] = PrefetchTask(self, id)
            return task

    def schedule_delete(self, id: int, delay: float) -> None:
        def do_delete() -> None:
            logger.info(f"已删除 {self.DIR} {id}")
            try_remove(f"{self.DIR}/{id}.json")
            try_remove(f"{self.DIR}/{id}")
            self.delete_tokens.pop(id, None)

        if token := self.delete_tokens.pop(id, None):
            token.cancel()
        if delay <= 0:
            do_delete()
        else:
            self.delete_tokens[id] = asyncio.get_running_loop().call_later(delay, do_delete)

    def clean(self) -> None:
        if self.ttl is None:
            return
        current_time = time.time()
        for file in try_scandir(self.DIR):
            if not file.name.endswith(".json"):
                continue
            with open(file.path) as f:
                cache = PrefetchInfo.model_validate(json.load(f))
                id = int(file.name.removesuffix(".json"))
                self.schedule_delete(id, self.ttl - (current_time - cache.time))

    async def stream(self, request: web.Request, id: int, prefetch: bool = True) -> web.StreamResponse:
        if not prefetch:
            response = await self.request(id)
            if isinstance(response, str):
                return web.Response(body=response, status=404)
            async with response:
                return await stream_response(request, response)
        try:
            with open(f"{self.DIR}/{id}.json") as f:
                cache = PrefetchInfo.model_validate(json.load(f))
            if self.ttl is None or time.time() - cache.time < self.ttl:
                if cache.error is not None:
                    return web.Response(body=cache.error, status=404)
                else:
                    return web.FileResponse(f"{self.DIR}/{id}")
        except FileNotFoundError:
            pass
        return await self.schedule(id).stream(request)

    def ensure(self, id: int) -> None:
        try:
            with open(f"{self.DIR}/{id}.json") as f:
                cache = PrefetchInfo.model_validate(json.load(f))
            if self.ttl is None or time.time() - cache.time < self.ttl:
                return
        except FileNotFoundError:
            pass
        self.schedule(id)


class SongPrefetcher(Prefetcher):
    DIR = "song_prefetch"

    def __init__(
        self,
        client: aiohttp.ClientSession,
        proxy: str | None,
        info_cache: SongInfoCache,
        ttl: float | None,
        retry_count: int | None,
        retry_4xx: bool,
        ngproxy: bool,
        assets_server: AssetsServer,
        target_dir: str | None,
    ) -> None:
        super().__init__(ttl)
        self.client = client
        self.proxy = proxy
        self.info_cache = info_cache
        self.retry_count = retry_count
        self.retry_4xx = retry_4xx
        self.ngproxy = ngproxy
        self.assets_server = assets_server
        self.target_dir = target_dir

    async def request(self, id: int) -> aiohttp.ClientResponse | str:
        url = None
        ngproxy_available = True
        retry_left = self.retry_count
        while True:
            if self.ngproxy and ngproxy_available:
                response = await self.client.get(f"https://ng.geometrydashchinese.com/api/{id}/download")
                logger.log("DEBUG" if response.ok else "WARNING", f"{response.status} {response.method} {response.url}")
                if response.ok:
                    return response
                await response.__aexit__(None, None, None)
                # NGProxy 似乎不返回 4xx，只返回 5xx，只是以防万一
                # EDIT：这个返回 403 https://ng.geometrydashchinese.com/api/826472/download
                if not self.retry_4xx and (400 <= response.status <= 499):
                    ngproxy_available = False
            if url is None:
                info = await self.info_cache.get(id)
                if isinstance(info, int):
                    return str(info)
                url = info.get(10)
                if not url or url == "CUSTOMURL":
                    url = f"{await self.assets_server()}/music/{id}.ogg"
            response = await self.client.get(url, proxy=self.proxy)
            if response.ok or (retry_left is not None and retry_left <= 0) or (400 <= response.status <= 499 and not self.retry_4xx):
                logger.log("DEBUG" if response.ok else "WARNING", f"{response.status} {response.method} {response.url}")
                return response
            await response.__aexit__(None, None, None)
            logger.warning(f"{response.status} {response.method} {response.url} 剩余 {retry_left} 次重试")
            retry_left = None if retry_left is None else retry_left - 1

    def ensure(self, id: int) -> None:
        if self.target_dir and (os.path.exists(f"{self.target_dir}/{id}.mp3") or os.path.exists(f"{self.target_dir}/{id}.ogg")):
            return
        super().ensure(id)


class SfxPrefetcher(Prefetcher):
    DIR = "sfx_prefetch"

    def __init__(
        self,
        client: aiohttp.ClientSession,
        proxy: str | None,
        ttl: float | None,
        retry_count: int | None,
        retry_4xx: bool,
        assets_server: AssetsServer,
        target_dir: str | None,
    ) -> None:
        super().__init__(ttl)
        self.client = client
        self.proxy = proxy
        self.retry_count = retry_count
        self.retry_4xx = retry_4xx
        self.assets_server = assets_server
        self.target_dir = target_dir

    async def request(self, id: int) -> aiohttp.ClientResponse:
        server = await self.assets_server()
        retry_left = self.retry_count
        while True:
            response = await self.client.get(f"{server}/sfx/s{id}.ogg", proxy=self.proxy)
            if response.ok or (retry_left is not None and retry_left <= 0) or (400 <= response.status <= 499 and not self.retry_4xx):
                logger.log("DEBUG" if response.ok else "WARNING", f"{response.status} {response.method} {response.url}")
                return response
            await response.__aexit__(None, None, None)
            logger.warning(f"{response.status} {response.method} {response.url} 剩余 {retry_left} 次重试")
            retry_left = None if retry_left is None else retry_left - 1

    def ensure(self, id: int) -> None:
        if self.target_dir and os.path.exists(f"{self.target_dir}/s{id}.ogg"):
            return
        super().ensure(id)

CONFIG = web.AppKey("CONFIG", Config)
HTTP_CLIENT = web.AppKey("HTTP_CLIENT", aiohttp.ClientSession)
BACKUP_SCHEDULER = web.AppKey("BACKUP_SCHEDULER", BackupScheduler)
API_MANAGER = web.AppKey("API_MANAGER", ApiManager)
SONG_INFO_CACHE = web.AppKey("SONG_INFO_CACHE", SongInfoCache)
SONG_PREFETCHER = web.AppKey("SONG_PREFETCHER", SongPrefetcher)
SFX_PREFETCHER = web.AppKey("SFX_PREFETCHER", SfxPrefetcher)
routes = web.RouteTableDef()
form_vaildator = TypeAdapter(dict[str, str])


@routes.get("/")
async def _(request: web.Request) -> web.Response:
    config = request.app[CONFIG]
    return web.Response(body=(
        f"Geometry Dash 本地同步 & 反向代理\n"
        f"将服务器地址设置为 {str(request.url.origin()).ljust(len(OFFICIAL_SERVER), '/')}\n"
        f"游戏服务器 {config.game_server}\n"
        f"备份服务器 {config.backup_server_repr}"
    ))


@routes.post("/{pad:/*}getAccountURL.php")
async def _(request: web.Request) -> web.StreamResponse:
    form = form_vaildator.validate_python(await request.post())
    account_id = int(form["accountID"])
    config = request.app[CONFIG]
    if not config.backup_enabled or not config.backup_auth.has_account(account_id):
        if not config.backup_server:
            return await request.app[API_MANAGER].getAccountURL.stream(request)
        return web.Response(body=str(config.backup_server).removesuffix("/"))
    return web.Response(body=str(request.url.origin()))


@routes.post("/database/accounts/backupGJAccountNew.php")
async def _(request: web.Request) -> web.Response:
    request = request.clone(client_max_size=30 * 1024 * 1024)
    form = form_vaildator.validate_python(await request.post())
    account_id = int(form.pop("accountID"))
    config = request.app[CONFIG]
    if not config.backup_enabled or not config.backup_auth.validate_gjp2(account_id, form["gjp2"]):
        return web.HTTPForbidden(body="-1")
    ccgamemanager, cclocallevels = form.pop("saveData").split(";")
    os.makedirs(f"accounts/{account_id}", exist_ok=True)
    with open(f"accounts/{account_id}/CCGameManager.xml.gz", "wb") as f:
        f.write(base64.urlsafe_b64decode(ccgamemanager))
    with open(f"accounts/{account_id}/CCLocalLevels.xml.gz", "wb") as f:
        f.write(base64.urlsafe_b64decode(cclocallevels))
    if config.backup_enabled != "local":
        if not config.backup_server:
            async with request.app[API_MANAGER].getAccountURL(data={"accountID": account_id, "type": 1, "secret": "Wmfd2893gb7"}) as response:
                data = await api_read(response)
                if isinstance(data, web.Response):
                    logger.warning(f"获取 {account_id} 的备份服务器失败，响应: {data.body!r}")
                    return data
                server = AnyUrl(data)
        else:
            server = config.backup_server
        request.app[BACKUP_SCHEDULER].schedule(account_id, BackupTask(server=server, token=form, retry_left=config.backup_retry_count))
    return web.Response(body="1")


@routes.post("/database/accounts/syncGJAccountNew.php")
async def _(request: web.Request) -> web.Response:
    form = form_vaildator.validate_python(await request.post())
    account_id = int(form["accountID"])
    config = request.app[CONFIG]
    if not config.backup_enabled or not config.backup_auth.validate_gjp2(account_id, form["gjp2"]):
        return web.HTTPForbidden(body="-1")
    try:
        with open(f"accounts/{account_id}/CCGameManager.xml.gz", "rb") as f:
            ccgamemanager = base64.urlsafe_b64encode(f.read()).decode()
        with open(f"accounts/{account_id}/CCLocalLevels.xml.gz", "rb") as f:
            cclocallevels = base64.urlsafe_b64encode(f.read()).decode()
    except FileNotFoundError:
        return web.Response(body="-1")
    return web.Response(body=f"{ccgamemanager};{cclocallevels};21;30;a;a")


@routes.post("/{pad:/*}accounts/loginGJAccount.php")
async def _(request: web.Request) -> web.Response:
    async with request.app[API_MANAGER]["accounts/loginGJAccount"](request) as response:
        data = await api_read(response)
        if isinstance(data, web.Response):
            return data
        account_id, uuid = data.split(",")
        form = form_vaildator.validate_python(await request.post())
        request.app[CONFIG].backup_auth.write_gjp2(int(account_id), form["gjp2"])
        return web.Response(body=data)


@routes.post("/{pad:/*}getGJSongInfo.php")
async def _(request: web.Request) -> web.StreamResponse:
    config = request.app[CONFIG]
    api = request.app[API_MANAGER]["/getGJSongInfo" if config.song_bypass_ngproxy else "getGJSongInfo"]
    if not config.song_enabled:
        return await api.stream(request)
    form = form_vaildator.validate_python(await request.post())
    song_id = int(form["songID"])
    info = await request.app[SONG_INFO_CACHE].get(song_id)
    if isinstance(info, int):
        return web.Response(body=str(info))
    url = info.get(10, "")
    if url and url != "CUSTOMURL":
        info[10] = f"{request.url.origin()}/song/{info[1]}"
    return web.Response(body=SongInfo.dump(info))


def process_song_list(cache: SongInfoCache, data: str, origin: str) -> str:
    songs = data.split("~:~") if data else []
    for i, song in enumerate(songs):
        info = SongInfo.load(song)
        cache.insert(int(info[1]), info)
        url = info.get(10, "")
        if url and url != "CUSTOMURL":
            info[10] = f"{origin}/song/{info[1]}"
        songs[i] = SongInfo.dump(info)
    return "~:~".join(songs)


@routes.post("/{pad:/*}getGJLevels21.php")
async def _(request: web.Request) -> web.StreamResponse:
    config = request.app[CONFIG]
    if not config.song_enabled:
        return await request.app[API_MANAGER].getGJLevels21.stream(request)
    async with request.app[API_MANAGER].getGJLevels21(request) as response:
        data = await api_read(response)
        if isinstance(data, web.Response):
            return data
        data = data.split("#")
        if len(data) >= 3:
            data[2] = process_song_list(request.app[SONG_INFO_CACHE], data[2], request.url.origin())
        return web.Response(body="#".join(data))


@routes.post("/{pad:/*}getCustomContentURL.php")
async def _(request: web.Request) -> web.StreamResponse:
    if not request.app[CONFIG].assets_enabled:
        return await request.app[API_MANAGER].getCustomContentURL.stream(request)
    return web.Response(body=f"{request.url.origin()}/assets")


@routes.get(r"/assets/music/{song_id:\d+}.ogg")
@routes.get(r"/assets/sfx/s{sfx_id:\d+}.ogg")
async def _(request: web.Request) -> web.StreamResponse:
    config = request.app[CONFIG]
    if not config.assets_enabled:
        return web.HTTPForbidden()

    if "song_id" in request.match_info:
        prefetcher = request.app[SONG_PREFETCHER]
        id = int(request.match_info["song_id"])
    else:
        prefetcher = request.app[SFX_PREFETCHER]
        id = int(request.match_info["sfx_id"])

    return await prefetcher.stream(request, id, config.prefetch)


@routes.get(r"/song/{song_id:\d+}")
async def _(request: web.Request) -> web.StreamResponse:
    config = request.app[CONFIG]
    if not config.song_enabled:
        return web.HTTPForbidden()

    return await request.app[SONG_PREFETCHER].stream(request, int(request.match_info["song_id"]), config.prefetch)


@routes.post("/{pad:/*}downloadGJLevel22.php")
async def _(request: web.Request) -> web.StreamResponse:
    async with request.app[API_MANAGER].downloadGJLevel22(request) as response:
        data = await api_read(response)
        if isinstance(data, web.Response):
            return data
        data = data.split("#")
        level = data[0].split(":")
        level = {int(level[i]): level[i + 1] for i in range(0, len(level), 2)}
        # 预载单首音乐意义不大
        # request.app[SONG_PREFETCHER].ensure(int(level[35]))  # song
        if 52 in level:  # songs
            for song_id in level[52].split(","):
                request.app[SONG_PREFETCHER].ensure(int(song_id))
        if 53 in level:  # sfx
            for sfx_id in level[53].split(","):
                request.app[SFX_PREFETCHER].ensure(int(sfx_id))
        if len(data) >= 5:
            data[4] = process_song_list(request.app[SONG_INFO_CACHE], data[4], request.url.origin())
        return web.Response(body="#".join(data))


@routes.post(r"/{pad:/*}{api:(accounts/)?[A-Za-z0-9]+}.php")
async def handle_proxy(request: web.Request) -> web.StreamResponse:
    return await request.app[API_MANAGER][request.match_info["api"]].stream(request)


async def setup_http_client(app: web.Application) -> AsyncGenerator[None, None]:
    http_client = app[HTTP_CLIENT] = aiohttp.ClientSession()
    config = app[CONFIG]
    app[API_MANAGER] = api_manager = ApiManager(http_client, str(config.game_server).removesuffix("/"), config.game_retry_count, config.game_retry_4xx, proxy=config.game_proxy_str)
    if config.assets_server is None:
        assets_server = AssetsServerCached(api_manager.getCustomContentURL, config.assets_server_ttl)
    else:
        assets_server = AssetsServerStatic(str(config.assets_server))
    if config.song_enabled:
        app[SONG_INFO_CACHE] = song_info_cache = SongInfoCache(api_manager["/getGJSongInfo" if config.song_bypass_ngproxy else "getGJSongInfo"], config.song_info_ttl)
        song_info_cache.clean()
        app[SONG_PREFETCHER] = song_prefetcher = SongPrefetcher(http_client, config.song_proxy_str, song_info_cache, config.prefetch_ttl, config.song_retry_count, config.song_retry_4xx, config.song_ngproxy, assets_server, config.prefetch_target_dir)
        song_prefetcher.clean()
    if config.assets_enabled:
        app[SFX_PREFETCHER] = sfx_prefetcher = SfxPrefetcher(http_client, config.song_proxy_str, config.prefetch_ttl, config.song_retry_count, config.song_retry_4xx, assets_server, config.prefetch_target_dir)
        sfx_prefetcher.clean()
    yield
    await http_client.close()


async def setup_backup_scheduler(app: web.Application) -> AsyncGenerator[None, None]:
    config = app[CONFIG]
    scheduler = app[BACKUP_SCHEDULER] = BackupScheduler(app[HTTP_CLIENT], config.backup_retry_interval, config.backup_retry_4xx, proxy=config.backup_proxy_str)
    try:
        with open("backup_tasks.json") as f:
            tasks = TypeAdapter(dict[int, BackupTask]).validate_python(json.load(f))
        if tasks:
            logger.info(f"发现 {len(tasks)} 个未上传成功的任务")
        for account_id, task in tasks.items():
            scheduler.schedule(account_id, task)
    except FileNotFoundError:
        pass
    yield
    with open("backup_tasks.json", "w") as f:
        pydantic_dump(scheduler.tasks, f)
    if scheduler.tasks:
        logger.info(f"已保存 {len(scheduler.tasks)} 个未上传成功的任务")


def aiohttp_print(text: str) -> None:
    for line in text.splitlines():
        logger.opt(depth=1).info(line)


def main() -> None:
    try:
        with open("config.json", "r") as f:
            config = Config.model_validate(json.load(f))
    except FileNotFoundError:
        config = Config()
    app = web.Application()
    app[CONFIG] = config
    app.add_routes(routes)
    app.cleanup_ctx.append(setup_http_client)
    if config.backup_enabled:
        app.cleanup_ctx.append(setup_backup_scheduler)
    logger.info("Geometry Dash 本地同步 & 反向代理")
    logger.info(f"游戏服务器 {config.game_server}")
    logger.info(f"备份服务器 {config.backup_server_repr}")
    web.run_app(app, host=str(config.host), port=config.port, print=aiohttp_print)


if __name__ == "__main__":
    main()
