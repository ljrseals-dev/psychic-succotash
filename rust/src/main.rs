//! ElevenX Ultra-Low Latency Streamer
//! Receives PCM from Python via shared memory / Unix socket,
//! packages into Opus (optional), streams over WebSocket.

mod ring_buffer;

use axum::{
    extract::ws::{Message, WebSocket, WebSocketUpgrade},
    response::IntoResponse,
    routing::get,
    Router,
};
use ring_buffer::SpscRingBuffer;
use std::sync::Arc;
use tower_http::cors::CorsLayer;
use tracing_subscriber;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let ring = Arc::new(SpscRingBuffer::new(65536));

    // In production: spawn a task that reads from shared memory / UDS
    // and pushes into the ring buffer.

    let app = Router::new()
        .route("/ws/audio", get(ws_handler))
        .route("/health", get(|| async { "ElevenX Streamer OK" }))
        .layer(CorsLayer::permissive())
        .with_state(ring);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await.unwrap();
    tracing::info!("ElevenX Rust Streamer listening on :8080");
    axum::serve(listener, app).await.unwrap();
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    axum::extract::State(ring): axum::extract::State<Arc<SpscRingBuffer>>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, ring))
}

async fn handle_socket(mut socket: WebSocket, ring: Arc<SpscRingBuffer>) {
    let mut buf = vec![0.0f32; 1024];
    loop {
        let n = ring.pop(&mut buf);
        if n > 0 {
            // Convert f32 → i16 PCM bytes for demo
            let mut bytes = Vec::with_capacity(n * 2);
            for &s in &buf[..n] {
                let sample = (s.clamp(-1.0, 1.0) * 32767.0) as i16;
                bytes.extend_from_slice(&sample.to_le_bytes());
            }
            if socket.send(Message::Binary(bytes.into())).await.is_err() {
                break;
            }
        } else {
            tokio::time::sleep(tokio::time::Duration::from_millis(2)).await;
        }
    }
}
