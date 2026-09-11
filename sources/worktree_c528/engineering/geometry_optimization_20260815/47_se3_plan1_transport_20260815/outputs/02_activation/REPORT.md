# SE3 candidate-owned activation and delayed-source preparation

Status: PASS__SE3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY

The package consumes 10 validated SE3 BUILDUP jobs and 1,015,492 generated primaries. Production is normalized inside each incident family as sum(RP)/sum(TT), retaining TT from zero-RP DAT.

It contains 4,153 state rows and 23,348 matched exact production positions. Every positive family source starts from 50,000 deterministic draws, retains indices 0,5,...,49995, and multiplies block flux by five for 10,000-block closure. The 7 positive-A15 cells each request 83,334 triggers and use their registered job seeds; 1 zero-A15 cells remain registered but are not launched. Every zero source carries a two-sided 95% 3.688879/sumTT upper-rate and a conservative saturation-factor<=1 A15 upper; known and unresolved holdouts remain separate.

The SIM inputs were read once for CC IP RP semantics and were not hashed. This stage is not detector-selected delayed-rate, common-response, mission, F3, or geometry-promotion authority.
