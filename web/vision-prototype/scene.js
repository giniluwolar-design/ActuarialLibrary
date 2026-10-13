// Three structural directions live in the prototype shell; this file supplies
// the shared, quiet spatial language for the reserving and annuity scenes.
const TAU = Math.PI * 2;
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

function rotate(point, rx, rz) {
  const cx = Math.cos(rx);
  const sx = Math.sin(rx);
  const cz = Math.cos(rz);
  const sz = Math.sin(rz);
  const y = point.y * cx - point.z * sx;
  const z = point.y * sx + point.z * cx;
  return { x: point.x * cz - y * sz, y: point.x * sz + y * cz, z };
}

function makeProjector(ctx, width, height, pose) {
  const scale = Math.min(width / 4.25, height / 2.95);
  const centerX = width * 0.5;
  const centerY = height * 0.52;
  const focal = 5.2;
  return point => {
    const turned = rotate(point, pose.rx, pose.rz);
    const depth = focal / (focal - turned.z);
    return {
      x: centerX + turned.x * scale * depth,
      y: centerY - turned.y * scale * depth,
      z: turned.z,
      depth,
    };
  };
}

function line(ctx, points, project, color, width, alpha = 1) {
  if (points.length < 2) return;
  ctx.beginPath();
  points.forEach((point, index) => {
    const p = project(point);
    if (index === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.strokeStyle = color;
  ctx.globalAlpha = alpha;
  ctx.lineWidth = width;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.stroke();
  ctx.globalAlpha = 1;
}

function drawReserving(ctx, width, height, pose) {
  const project = makeProjector(ctx, width, height, pose);
  const rows = 17;
  const points = [];
  const surface = (row, col) => {
    const t = row / rows;
    const across = row ? col / row : 0.5;
    const x = (across - 0.5) * 2.9 * t;
    const z = (t - 0.5) * 2.15;
    const wave = Math.sin(across * Math.PI * 3 + t * 3.4) * 0.075;
    const rise = Math.pow(t, 1.45) * 0.18;
    return { x, y: wave + rise + 0.045 * Math.sin(t * Math.PI), z };
  };

  for (let row = 0; row <= rows; row += 1) {
    points[row] = [];
    for (let col = 0; col <= row; col += 1) points[row][col] = surface(row, col);
  }

  const triangles = [];
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col <= row; col += 1) {
      const a = points[row][col];
      const b = points[row + 1][col];
      const c = points[row + 1][col + 1];
      triangles.push([a, b, c]);
      if (col < row) triangles.push([a, points[row][col + 1], c]);
    }
  }

  // A soft under-fold gives the paper-thin triangle a little depth.
  ctx.save();
  ctx.shadowColor = 'rgba(191, 122, 76, 0.18)';
  ctx.shadowBlur = Math.min(width, height) * 0.045;
  ctx.beginPath();
  for (let index = 0; index <= rows; index += 1) {
    const p = project(points[rows][index]);
    if (index === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  }
  const apex = project(points[0][0]);
  ctx.lineTo(apex.x, apex.y);
  ctx.closePath();
  ctx.fillStyle = 'rgba(107, 69, 49, 0.15)';
  ctx.fill();
  ctx.restore();

  const painted = triangles.map((triangle, index) => {
    const projected = triangle.map(project);
    return { triangle, projected, depth: projected.reduce((sum, p) => sum + p.z, 0) / 3, index };
  }).sort((a, b) => a.depth - b.depth);
  for (const { projected, index } of painted) {
    const depthTone = clamp((projected.reduce((sum, p) => sum + p.z, 0) / 3 + 1.4) / 2.8, 0, 1);
    ctx.beginPath();
    ctx.moveTo(projected[0].x, projected[0].y);
    ctx.lineTo(projected[1].x, projected[1].y);
    ctx.lineTo(projected[2].x, projected[2].y);
    ctx.closePath();
    ctx.fillStyle = index % 2
      ? `rgba(193, 126, 79, ${0.025 + depthTone * 0.027})`
      : `rgba(233, 180, 128, ${0.018 + depthTone * 0.026})`;
    ctx.fill();
  }

  // Fine actuarial-development grid, eased at the folded edge.
  ctx.strokeStyle = 'rgba(221, 169, 124, 0.32)';
  ctx.lineWidth = Math.max(0.55, Math.min(width, height) / 650);
  ctx.lineJoin = 'round';
  for (let row = 1; row <= rows; row += 1) {
    ctx.beginPath();
    for (let col = 0; col <= row; col += 1) {
      const p = project(points[row][col]);
      if (col === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
  for (let col = 0; col <= rows; col += 1) {
    ctx.beginPath();
    for (let row = col; row <= rows; row += 1) {
      const p = project(points[row][col]);
      if (row === col) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }

  // Copper contour lines are interpolated across the sheet, not chart axes.
  const heightAt = p => p.y - 0.18 * Math.pow((p.z / 2.15) + 0.5, 1.45);
  const heights = triangles.flatMap(triangle => triangle.map(heightAt));
  const low = Math.min(...heights);
  const high = Math.max(...heights);
  const contourCount = 6;
  for (let band = 1; band <= contourCount; band += 1) {
    const level = low + (high - low) * band / (contourCount + 1);
    for (const triangle of triangles) {
      const hits = [];
      for (let edge = 0; edge < 3; edge += 1) {
        const a = triangle[edge];
        const b = triangle[(edge + 1) % 3];
        const va = heightAt(a) - level;
        const vb = heightAt(b) - level;
        if ((va < 0 && vb >= 0) || (vb < 0 && va >= 0)) {
          const ratio = va / (va - vb);
          hits.push({ x: a.x + (b.x - a.x) * ratio, y: a.y + (b.y - a.y) * ratio, z: a.z + (b.z - a.z) * ratio });
        }
      }
      if (hits.length === 2) line(ctx, hits, project, '#dfac78', Math.max(0.65, Math.min(width, height) / 540), 0.48);
    }
  }

  // A restrained doubled edge suggests a folded, translucent material.
  const edge = points[rows];
  line(ctx, edge, project, '#d59a6f', Math.max(0.8, Math.min(width, height) / 420), 0.72);
  line(ctx, [points[0][0], ...Array.from({ length: rows + 1 }, (_, index) => points[rows - index][0])], project, '#e3b184', 0.8, 0.5);
}

function orbitalPoint(t, orbit, offset = 0) {
  const angle = t + offset;
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  const x = orbit.rx * c;
  const y = orbit.ry * s;
  const z = orbit.bow * Math.sin(2 * angle + orbit.phase);
  return rotate({ x, y, z }, orbit.tilt, orbit.bank);
}

function drawRibbon(ctx, project, orbit, color, alpha, width, mobile) {
  const count = mobile ? 104 : 164;
  const halfWidth = mobile ? 0.012 : 0.018;
  const upper = [];
  const lower = [];
  const center = [];
  for (let index = 0; index <= count; index += 1) {
    const t = TAU * index / count;
    const p = orbitalPoint(t, orbit);
    const tangent = orbitalPoint(t + 0.008, orbit);
    let nx = -(tangent.y - p.y);
    let ny = tangent.x - p.x;
    const length = Math.hypot(nx, ny) || 1;
    nx /= length;
    ny /= length;
    const lift = halfWidth;
    upper.push(project({ x: p.x + nx * lift, y: p.y + ny * lift, z: p.z + 0.01 }));
    lower.push(project({ x: p.x - nx * lift, y: p.y - ny * lift, z: p.z - 0.01 }));
    center.push(p);
  }

  ctx.beginPath();
  upper.forEach((p, index) => index ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
  for (let index = lower.length - 1; index >= 0; index -= 1) ctx.lineTo(lower[index].x, lower[index].y);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.globalAlpha = alpha;
  ctx.fill();
  ctx.globalAlpha = 1;
  line(ctx, center, project, color, Math.max(0.75, width), Math.min(0.82, alpha + 0.2));
  return center;
}

function drawAnnuity(ctx, width, height, pose, mobile) {
  const project = makeProjector(ctx, width, height, pose);
  const firstOrbit = { rx: 1.36, ry: 0.78, bow: 0.055, phase: 0.2, tilt: -0.34, bank: 0.08 };
  const secondOrbit = { rx: 1.2, ry: 0.69, bow: 0.065, phase: 1.15, tilt: 0.31, bank: 0.46 };
  const first = drawRibbon(ctx, project, firstOrbit, '#a3cdb9', 0.27, 1.05, mobile);
  const second = drawRibbon(ctx, project, secondOrbit, '#c1d9cb', 0.18, 0.9, mobile);

  // Sparse date markers: tiny light caught on the path, never a data plot.
  const stride = mobile ? 28 : 21;
  for (const [orbit, color, phase] of [[firstOrbit, '#b8d7c8', 0], [secondOrbit, '#d2e5da', 5]]) {
    for (let index = phase; index < stride * 2; index += stride) {
      const p = project(orbitalPoint(TAU * index / (stride * 2), orbit));
      const radius = mobile ? 1.45 : 2.05;
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius * p.depth, 0, TAU);
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.78;
      ctx.fill();
      ctx.globalAlpha = 1;
    }
  }

  // Quiet shared origin and two endpoints make the paired paths readable.
  const origin = project({ x: 0, y: 0, z: 0.02 });
  ctx.beginPath();
  ctx.arc(origin.x, origin.y, mobile ? 1.7 : 2.35, 0, TAU);
  ctx.fillStyle = '#d9e8df';
  ctx.globalAlpha = 0.58;
  ctx.fill();
  ctx.globalAlpha = 1;
  void first;
  void second;
}

/**
 * Mount one decorative, data-free spatial scene into an existing canvas.
 * Accessible meaning and all interface text belong to the surrounding DOM.
 */
export function mountScene(canvas, { kind = 'reserving', reducedMotion = false } = {}) {
  if (!(canvas instanceof HTMLCanvasElement)) throw new TypeError('mountScene expects a canvas element');
  if (kind !== 'reserving' && kind !== 'annuity') throw new RangeError(`Unknown scene: ${kind}`);

  const ctx = canvas.getContext('2d', { alpha: true, desynchronized: true });
  if (!ctx) throw new Error('Canvas 2D is unavailable');

  let cssWidth = 0;
  let cssHeight = 0;
  let dpr = 1;
  let pointerX = 0;
  let pointerY = 0;
  let visible = true;
  let stopped = false;
  let frame = 0;
  let lastPaint = 0;
  let mobile = window.innerWidth <= 600;
  const staticPose = { rx: kind === 'reserving' ? 0.88 : 0.22, rz: kind === 'reserving' ? -0.1 : -0.14 };

  const paint = time => {
    if (stopped || cssWidth <= 0 || cssHeight <= 0) return;
    const motion = reducedMotion || mobile ? 0 : time * 0.000012;
    const pose = {
      rx: staticPose.rx + pointerY * 0.075 + Math.sin(motion) * 0.018,
      rz: staticPose.rz + pointerX * 0.075 + Math.cos(motion * 0.72) * 0.016,
    };
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssWidth, cssHeight);
    if (kind === 'reserving') drawReserving(ctx, cssWidth, cssHeight, pose);
    else drawAnnuity(ctx, cssWidth, cssHeight, pose, mobile);
  };

  const schedule = () => {
    if (!stopped && visible && !reducedMotion && !mobile && !document.hidden && !frame) {
      frame = requestAnimationFrame(tick);
    }
  };
  const tick = time => {
    frame = 0;
    if (stopped || !visible || document.hidden) return;
    if (time - lastPaint >= 66) {
      paint(time);
      lastPaint = time;
    }
    schedule();
  };
  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    cssWidth = rect.width;
    cssHeight = rect.height;
    dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    mobile = window.innerWidth <= 600;
    canvas.width = Math.max(1, Math.round(cssWidth * dpr));
    canvas.height = Math.max(1, Math.round(cssHeight * dpr));
    paint(performance.now());
    schedule();
  };
  const onPointerMove = event => {
    const rect = canvas.getBoundingClientRect();
    pointerX = clamp((event.clientX - rect.left) / Math.max(rect.width, 1) * 2 - 1, -1, 1);
    pointerY = clamp((event.clientY - rect.top) / Math.max(rect.height, 1) * 2 - 1, -1, 1);
    if (reducedMotion || mobile) return;
    schedule();
  };
  const onPointerLeave = () => {
    pointerX = 0;
    pointerY = 0;
    if (!reducedMotion && !mobile) schedule();
  };
  const onVisibilityChange = () => {
    if (document.hidden && frame) cancelAnimationFrame(frame);
    if (document.hidden) frame = 0;
    else {
      paint(performance.now());
      schedule();
    }
  };
  const observer = new ResizeObserver(resize);
  const intersection = new IntersectionObserver(entries => {
    visible = entries.some(entry => entry.isIntersecting);
    if (visible) {
      paint(performance.now());
      schedule();
    } else if (frame) {
      cancelAnimationFrame(frame);
      frame = 0;
    }
  });

  observer.observe(canvas);
  intersection.observe(canvas);
  canvas.addEventListener('pointermove', onPointerMove, { passive: true });
  canvas.addEventListener('pointerleave', onPointerLeave, { passive: true });
  document.addEventListener('visibilitychange', onVisibilityChange);
  window.addEventListener('resize', resize, { passive: true });
  resize();

  return () => {
    stopped = true;
    if (frame) cancelAnimationFrame(frame);
    observer.disconnect();
    intersection.disconnect();
    canvas.removeEventListener('pointermove', onPointerMove);
    canvas.removeEventListener('pointerleave', onPointerLeave);
    document.removeEventListener('visibilitychange', onVisibilityChange);
    window.removeEventListener('resize', resize);
  };
}
