# Calculation Core v1 — frozen specification (2026-10-19)

Status: **experimental implementation; not clinically validated**. This freeze defines interfaces and math, not clinical accuracy or implant selection.

Pipeline: M0 RAW → M1 GEOMETRY → M2 KINEMATICS → M3 REGIONAL → M4 RECONSTRUCTION (future).

- M0: immutable original anatomical landmarks, source image references, calibration, orientation, provenance.
- M1: signed intervertebral endplate angle; translation along caudal AP endplate; height profile on common AP support; metric heights only with verified calibration.
- M2: FLEX/EXT signed delta and absolute angular excursion. ICR **pending** until image-registration quality, orientation and scaling are validated; never fabricate an ICR.
- M3: all 21 regional **direct Cobb** windows. Important: sums of disc IVAs do not generally equal direct Cobb across vertebrae, because within-body superior/inferior wedge angles intervene. Preserve both as distinct metrics.
- M4: **not implemented**. Cage height/angle/position cannot predict final vertebral pose, clinical adjacent-level demand, subsidence or force without manufacturer geometry, constraints and a validated model. No 'optimal' surgical cage or score is asserted.

Each value must retain provenance RAW/DERIVED/NORMALIZED/SIMULATED and QC. Never let failed body QC cascade to a valid two-point angle; never assume reflected images preserve angle sign. Height-profile sign requires orientation QC. No slopes/cSVA without confirmed horizontal; no millimeters without calibrated scale.

Quick start:
```bash
python -m unittest discover -s tests -v
python -m compileall -q ONeSpineCRxLib
```

API: `from ONeSpineCRxLib.calculation_core_v1 import analyze` with `analyze({"lat":{"points": {...}, "mm_per_unit": None}, ...})`.

Clinical deployment requires validation against manual measurements, image-based landmark QC, repeatability, and 3D Slicer integration. Do not use this experimental output alone to determine surgical levels or implant dimensions.
