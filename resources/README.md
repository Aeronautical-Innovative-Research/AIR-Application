# Reference resources

- `manuals/`: original DSA3217 datasheet, manual, and quickstart PDFs.
- `examples/`: original pickle fixture and CSV export. The new app does not deserialize pickles.
- `legacy/`: original windows and backend, retained for reference; not used by the application.

The acquisition implementation follows the supplied Manual's software section:
SCAN (printed p. 38), STATUS/STOP (p. 40), scan variables (pp. 42–45).
Live acquisition uses ASCII FORMAT=0 with 16 channel records per frame.

Additional implemented references: warm-up (printed p. 12), error buffer readout
(p. 26), identification readout (p. 32), and scan settings readout (p. 36).
Diagnostic actions are read-only; they do not clear stored errors or modify
identification/network variables. PDFs remain documentation files, not app controls.
