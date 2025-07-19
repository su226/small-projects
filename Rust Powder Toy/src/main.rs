use bevy::image::ImageSampler;
use bevy::prelude::*;
use bevy::render::{
    render_asset::RenderAssetUsages,
    render_resource::{Extent3d, TextureDimension, TextureFormat},
};
use bevy::window::WindowResized;
use rand::seq::SliceRandom;
use rand::Rng;

use crate::fps_counter::FpsCounterPlugin;

mod fps_counter;

const SAND_ACCELERATION: f32 = 0.4;
const SAND_MAX_SPEED: f32 = 8.0;

#[derive(Clone, PartialEq)]
enum ParticleType {
    Air,
    Sand,
    Wood,
}

#[derive(Clone)]
struct Particle {
    p_type: ParticleType,
    x: u32,
    y: u32,
    dx: f32,
    dy: f32,
    vx: f32,
    vy: f32,
    color: Color,
    dirty: bool,
    updated: bool,
}

const GRID_WIDTH: u32 = 256;
const GRID_HEIGHT: u32 = 256;
const BRUSH_SIZE: i32 = 5;

#[derive(Component)]
struct Grid {
    particles: Vec<Particle>,
}

impl Grid {
    fn new() -> Self {
        let mut particles = Vec::new();
        for y in 0..GRID_HEIGHT {
            for x in 0..GRID_WIDTH {
                particles.push(Particle {
                    p_type: ParticleType::Air,
                    x,
                    y,
                    dx: 0.,
                    dy: 0.,
                    vx: 0.,
                    vy: 0.,
                    color: Color::NONE,
                    dirty: false,
                    updated: false,
                });
            }
        }
        Self {
            particles: particles,
        }
    }

    fn get(&self, x: u32, y: u32) -> Option<&Particle> {
        if x >= GRID_WIDTH || y >= GRID_HEIGHT {
            return None
        }
        Some(&self.particles[(y * GRID_WIDTH + x) as usize])
    }

    fn get_mut(&mut self, x: u32, y: u32) -> Option<&mut Particle> {
        if x >= GRID_WIDTH || y >= GRID_HEIGHT {
            return None
        }
        Some(&mut self.particles[(y * GRID_WIDTH + x) as usize])
    }

    fn set(&mut self, x: u32, y: u32, p_type: ParticleType) -> bool {
        if x >= GRID_WIDTH || y >= GRID_HEIGHT {
            return false;
        }
        let particle = &mut self.particles[(y * GRID_WIDTH + x) as usize];
        if particle.p_type == p_type {
            return false;
        }
        particle.p_type = p_type;
        particle.vx = 0.;
        particle.vy = 0.;
        particle.dx = 0.;
        particle.dy = 0.;
        let mut hsla: Hsla = match particle.p_type {
            ParticleType::Air => Color::NONE,
            ParticleType::Sand => {
                Color::srgb_u8(220, 177, 89)
            }
            ParticleType::Wood => {
                Color::srgb_u8(70, 40, 29)
            },
        }.into();
        let mut rng = rand::rng();
        hsla.saturation = (hsla.saturation() + rng.random_range(-0.2..=0.0)).clamp(0.0, 1.0);
        hsla.lightness = (hsla.luminance() + rng.random_range(-0.1..=0.1)).clamp(0.0, 1.0);
        particle.color = hsla.into();
        particle.dirty = true;
        true
    }

    fn swap(&mut self, x1: u32, y1: u32, x2: u32, y2: u32) {
        let i = (y1 * GRID_WIDTH + x1) as usize;
        let j = (y2 * GRID_WIDTH + x2) as usize;
        self.particles.swap(i, j);
        self.particles[i].x = x1;
        self.particles[i].y = y1;
        self.particles[i].dirty = true;
        self.particles[j].x = x2;
        self.particles[j].y = y2;
        self.particles[j].dirty = true;
    }

    fn update(&mut self) {
        let total_count = (GRID_WIDTH * GRID_HEIGHT) as usize;
        let mut queue: Vec<usize> = (0..total_count).collect();
        for i in queue.iter() {
            self.particles[*i].updated = false;
        }
        let mut rng = rand::rng();
        queue.shuffle(&mut rng);
        let mut updated_count = 0;
        while updated_count < total_count {
            for i in queue.iter() {
                let particle = &mut self.particles[*i];
                if particle.updated {
                    continue;
                }
                particle.updated = true;
                updated_count += 1;
                match particle.p_type {
                    ParticleType::Air => {},
                    ParticleType::Sand => {
                        let current_x = particle.x;
                        let mut current_y = particle.y;
                        if let Some(down) = self.get(current_x, current_y + 1) && down.p_type == ParticleType::Air {
                            let particle = self.get_mut(current_x, current_y).unwrap();
                            particle.vy = (particle.vy + SAND_ACCELERATION).min(SAND_MAX_SPEED);
                            let amount = particle.vy + particle.dy;
                            for _ in 0..amount as u32 {
                                if let Some(down) = self.get(current_x, current_y + 1) && down.p_type == ParticleType::Air {
                                    self.swap(current_x, current_y, current_x, current_y + 1);
                                    current_y += 1;
                                } else {
                                    break;
                                }
                            }
                            let particle = self.get_mut(current_x, current_y).unwrap();
                            particle.dy = amount - amount.floor();
                        } else {
                            let particle = self.get_mut(current_x, current_y).unwrap();
                            particle.vy = 0.0;
                            particle.dy = 0.0;
                            if let Some(down) = self.get(current_x, current_y + 1) && down.p_type != ParticleType::Air {
                                let move_downleft = if 
                                    current_x > 0
                                    && let Some(left) = self.get(current_x - 1, current_y)
                                    && let Some(downleft) = self.get(current_x - 1, current_y + 1)
                                {
                                    left.p_type == ParticleType::Air && downleft.p_type == ParticleType::Air
                                } else {
                                    false
                                };
                                let move_downright = if
                                    let Some(right) = self.get(current_x + 1, current_y)
                                    && let Some(downright) = self.get(current_x + 1, current_y + 1)
                                {
                                    right.p_type == ParticleType::Air && downright.p_type == ParticleType::Air
                                } else {
                                    false
                                };
                                if move_downleft && move_downright {
                                    if rng.random_bool(0.5) {
                                        self.swap(current_x, current_y, current_x - 1, current_y + 1);
                                    } else {
                                        self.swap(current_x, current_y, current_x + 1, current_y + 1);
                                    }
                                } else if move_downleft {
                                    self.swap(current_x, current_y, current_x - 1, current_y + 1);
                                } else if move_downright {
                                    self.swap(current_x, current_y, current_x + 1, current_y + 1);
                                }
                            }
                        }
                    },
                    ParticleType::Wood => {},
                }
            }
        }
    }
}

#[derive(Resource)]
struct PrevMouseCoords(Option<(u32, u32)>);

fn setup(mut commands: Commands, mut images: ResMut<Assets<Image>>) {
    commands.spawn(Camera2d);

    let mut image = Image::new_fill(
        Extent3d {
            width: GRID_WIDTH,
            height: GRID_HEIGHT,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        &[0; 4],
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::MAIN_WORLD | RenderAssetUsages::RENDER_WORLD,
    );
    image.sampler = ImageSampler::nearest();

    commands.spawn((
        Sprite::from_image(images.add(image)),
        Transform {
            ..default()
        },
        Grid::new()),
    );
}

fn get_mouse_coords(window: &Window, transform: &Transform) -> Option<(u32, u32)> {
    let position = match window.cursor_position() {
        Some(position) => position,
        None => return None,
    };
    let Vec2 { x: width, y: height} = window.size();
    let origin_x = (width - GRID_HEIGHT as f32 * transform.scale.x) / 2. + transform.translation.x;
    let origin_y = (height - GRID_HEIGHT as f32 * transform.scale.y) / 2. - transform.translation.y;
    let world_x = (position.x - origin_x) / transform.scale.x;
    let world_y = (position.y - origin_y) / transform.scale.y;
    if world_x < 0. || world_y < 0. {
        return None;
    }
    let world_x = world_x.floor() as u32;
    let world_y = world_y.floor() as u32;
    if world_x >= GRID_WIDTH || world_y >= GRID_HEIGHT {
        return None;
    }
    Some((world_x, world_y))
}

fn render(
    mut grid: Single<&mut Grid>,
    sprite: Single<&Sprite, With<Grid>>,
    transform: Single<&Transform, With<Grid>>,
    mut images: ResMut<Assets<Image>>,
    window: Single<&Window>,
    mut prev_mouse_coords: ResMut<PrevMouseCoords>,
) {
    let image = images.get_mut(&sprite.image).unwrap();
    for x in 0..GRID_WIDTH {
        for y in 0..GRID_HEIGHT {
            let particle = &mut grid.particles[(y * GRID_WIDTH + x) as usize];
            if particle.dirty {
                image.set_color_at(x, y, particle.color).unwrap();
                particle.dirty = false;
            }
        }
    }
    if let PrevMouseCoords(Some((x, y))) = *prev_mouse_coords {
        for x_offset in -BRUSH_SIZE..=BRUSH_SIZE {
            for y_offset in -BRUSH_SIZE..=BRUSH_SIZE {
                let x = x as i32 + x_offset;
                let y = y as i32 + y_offset;
                if x < 0 || x >= GRID_WIDTH as i32 || y < 0 || y >= GRID_HEIGHT as i32 || (x_offset * x_offset + y_offset * y_offset) > BRUSH_SIZE * BRUSH_SIZE {
                    continue;
                }
                let x = x as u32;
                let y = y as u32;
                let color = grid.particles[(y * GRID_WIDTH + x) as usize].color;
                image.set_color_at(x, y, color).unwrap();
            }
        }
    }
    let mouse_coords = get_mouse_coords(&window, &transform);
    if let Some((x, y)) = mouse_coords {
        for x_offset in -BRUSH_SIZE..=BRUSH_SIZE {
            for y_offset in -BRUSH_SIZE..=BRUSH_SIZE {
                let x = x as i32 + x_offset;
                let y = y as i32 + y_offset;
                if x < 0 || x >= GRID_WIDTH as i32 || y < 0 || y >= GRID_HEIGHT as i32 || (x_offset * x_offset + y_offset * y_offset) > BRUSH_SIZE * BRUSH_SIZE {
                    continue;
                }
                let x = x as u32;
                let y = y as u32;
                let color = grid.particles[(y * GRID_WIDTH + x) as usize].color.to_srgba();
                image.set_color_at(x, y, Color::srgba(1. - color.red, 1. - color.green, 1. - color.blue, 1.)).unwrap();
            }
        }
    }
    prev_mouse_coords.0 = mouse_coords;
}

fn on_resize(
    mut transform: Single<&mut Transform, With<Grid>>,
    mut resize_reader: EventReader<WindowResized>,
) {
    let Some(resize) = resize_reader.read().last() else { return };
    let scale = f32::max(f32::min(resize.width / GRID_WIDTH as f32, resize.height / GRID_HEIGHT as f32).floor(), 1.);
    transform.scale.x = scale;
    transform.scale.y = scale;
    let width = GRID_WIDTH * scale as u32;
    let height = GRID_HEIGHT * scale as u32;
    let x_center = resize.width / 2.;
    let y_center = resize.height / 2.;
    transform.translation.x = x_center - x_center.floor() - (if width % 2 == 0 { 0. } else { 0.5 });
    transform.translation.y = y_center - y_center.floor() - (if height % 2 == 0 { 0. } else { 0.5 });
}

fn fixed_update(
    mut entity: Single<(&mut Grid, &Transform)>,
    window: Single<&Window>,
    mouse_button_input: Res<ButtonInput<MouseButton>>,
) {
    let transform = entity.1;
    let coords = get_mouse_coords(*window, transform);
    let grid = entity.0.as_mut();
    if let Some((x, y)) = coords {
        for x_offset in -BRUSH_SIZE..=BRUSH_SIZE {
            for y_offset in -BRUSH_SIZE..=BRUSH_SIZE {
                let x = x as i32 + x_offset;
                let y = y as i32 + y_offset;
                if x < 0 || x >= GRID_WIDTH as i32 || y < 0 || y >= GRID_HEIGHT as i32 || (x_offset * x_offset + y_offset * y_offset) > 25 {
                    continue;
                }
                let x = x as u32;
                let y = y as u32;
                if mouse_button_input.pressed(MouseButton::Left) {
                    grid.set(x, y, ParticleType::Sand);
                } else if mouse_button_input.pressed(MouseButton::Right) {
                    grid.set(x, y, ParticleType::Wood);
                }
            }
        }
    }
    grid.update();
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(FpsCounterPlugin)
        .add_systems(Startup, setup)
        .add_systems(Update, (render, on_resize))
        .add_systems(FixedUpdate, fixed_update)
        .insert_resource(PrevMouseCoords(None))
        .run();
}
