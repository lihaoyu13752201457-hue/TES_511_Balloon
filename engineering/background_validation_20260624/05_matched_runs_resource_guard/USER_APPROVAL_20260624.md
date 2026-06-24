# User Approval - BGO Matched Simulation

Date: 2026-06-24

User instruction:

> 那你还是按照harness engineering的逻辑来 但是我允许你进行BGO的全流程模拟 你根据HARNESS ENGINEERING保证你BOG模拟没有跑偏

Interpretation:

- The previous `BLOCKED_RESOURCE_APPROVAL` condition is lifted by explicit user
  approval for BGO full-workflow simulation.
- HARNESS staging still applies: run P0 syntax/geometry smoke, then P1 pilot,
  then P2 matched production only after the earlier stages pass.
- Existing CsI/fix5 authority outputs must not be overwritten.
- BGO outputs must remain isolated under the engineering validation tree unless
  a later explicit promotion decision says otherwise.

