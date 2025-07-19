use bevy::{
    diagnostic::{Diagnostic, DiagnosticPath, Diagnostics, DiagnosticsStore, FrameTimeDiagnosticsPlugin, RegisterDiagnostic},
    prelude::*,
};

pub const TPS: DiagnosticPath = DiagnosticPath::const_new("tps");

pub struct FpsCounterPlugin;

impl Plugin for FpsCounterPlugin {
    fn build(&self, app: &mut App) {
        app.add_plugins(FrameTimeDiagnosticsPlugin::default())
            .add_systems(Startup, spawn_text)
            .add_systems(Update, update)
            .add_systems(FixedUpdate, count_tps)
            .register_diagnostic(
                Diagnostic::new(TPS)
                    .with_max_history_length(120)
                    .with_smoothing_factor(0.01652892561983471),
            )
            .insert_resource(LastTick(0.0));
    }
}

#[derive(Resource)]
pub struct LastTick(f64);

#[derive(Component)]
pub struct FpsCounterText;

fn update(
    diagnostics: Res<DiagnosticsStore>,
    entity: Single<Entity, With<FpsCounterText>>,
    mut writer: TextUiWriter,
) {
    let fps = diagnostics
        .get(&FrameTimeDiagnosticsPlugin::FPS)
        .and_then(|fps| fps.average());

    let fps_text = if let Some(fps) = fps {
        format!("FPS: {:.0}", fps)
    } else {
        "FPS: ???".into()
    };

    let tps = diagnostics
        .get(&TPS)
        .and_then(|tps| tps.average()); 

    let tps_text = if let Some(tps) = tps {
        format!("TPS: {:.0}", tps)
    } else {
        "TPS: ???".into()
    };

    *writer.text(*entity, 0) = format!("{}\n{}", fps_text, tps_text);
}

fn spawn_text(mut commands: Commands) {
    commands.spawn((
        Text::default(),
        TextFont::default(),
        TextColor::default(),
        FpsCounterText
    ));
}

fn count_tps(mut diagnostics: Diagnostics, time: Res<Time<Real>>, mut last_tick: ResMut<LastTick>) {
    let current = time.elapsed_secs_f64();
    let delta = current - last_tick.0;
    if delta != 0.0 {
        diagnostics.add_measurement(&TPS, || 1.0 / delta);
    }
    last_tick.0 = current;
}
