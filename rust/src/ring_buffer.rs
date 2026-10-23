//! Lock-free SPSC ring buffer for zero-copy PCM transfer
//! between Python producer and Rust consumer.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::cell::UnsafeCell;

pub struct SpscRingBuffer {
    buffer: Box<[UnsafeCell<f32>]>,
    capacity: usize,
    write_pos: AtomicUsize,
    read_pos: AtomicUsize,
}

unsafe impl Send for SpscRingBuffer {}
unsafe impl Sync for SpscRingBuffer {}

impl SpscRingBuffer {
    pub fn new(capacity: usize) -> Self {
        let mut vec = Vec::with_capacity(capacity);
        for _ in 0..capacity {
            vec.push(UnsafeCell::new(0.0f32));
        }
        Self {
            buffer: vec.into_boxed_slice(),
            capacity,
            write_pos: AtomicUsize::new(0),
            read_pos: AtomicUsize::new(0),
        }
    }

    pub fn push(&self, samples: &[f32]) -> usize {
        let mut written = 0;
        let mut w = self.write_pos.load(Ordering::Relaxed);
        let r = self.read_pos.load(Ordering::Acquire);

        for &s in samples {
            let next = (w + 1) % self.capacity;
            if next == r {
                break; // full
            }
            unsafe {
                *self.buffer[w].get() = s;
            }
            w = next;
            written += 1;
        }
        self.write_pos.store(w, Ordering::Release);
        written
    }

    pub fn pop(&self, out: &mut [f32]) -> usize {
        let mut read = 0;
        let mut r = self.read_pos.load(Ordering::Relaxed);
        let w = self.write_pos.load(Ordering::Acquire);

        while read < out.len() && r != w {
            unsafe {
                out[read] = *self.buffer[r].get();
            }
            r = (r + 1) % self.capacity;
            read += 1;
        }
        self.read_pos.store(r, Ordering::Release);
        read
    }

    pub fn available(&self) -> usize {
        let w = self.write_pos.load(Ordering::Acquire);
        let r = self.read_pos.load(Ordering::Acquire);
        if w >= r {
            w - r
        } else {
            self.capacity - r + w
        }
    }
}
