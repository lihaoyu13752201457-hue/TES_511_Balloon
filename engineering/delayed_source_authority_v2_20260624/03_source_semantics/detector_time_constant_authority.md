# DetectorTimeConstant Authority

Installed parser evidence:
- `MCParameterFile.cc:188-191` parses `DetectorTimeConstant <seconds>` and multiplies the token by `s`.
- `MCParameterFile.cc:2998-3006` forwards that value to activators through `SetHalfLifeCutOff()`.
- `MCSteppingAction.cc:980-994` and `1012-1022` compare decay delays against `m_DetectorTimeConstant` in activation buildup and activation delayed-decay modes.

Authority for subsequent Phase-2 source cards:
- Use `DetectorTimeConstant 1e-9` unless a later gate explicitly changes the timing contract.
- WP06 still needs to audit final generated cards and logs; WP03 only establishes parser semantics.
