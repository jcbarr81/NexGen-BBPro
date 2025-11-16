## Things to look at

- Simulation injuries are disabled by default (set `PB_ENABLE_SIM_INJURIES=1` to opt back in once stats stabilize).
- Investigate why the walk scenario (test_walk_records_stats) now produces an out before layering in calibration changes.
- Resolve the legacy tests/test_playbalance_config.py expectation mismatch so the config suite can pass cleanly before broader integration.
- Directive rate is still high (~1.45 per PA). If you roll this straight into production you’ll see more waste/foul pitches than MLB norms. We may want to add smarter caps (count/inning aware) or dial the target/tolerance down further.
- Legacy consumers still see simulated_pitches values because recovery tooling reads the old field; they’re harmless (always zero) but it’d be cleaner to scrub or repurpose them.
- No UI exposure yet—owners can see the calibration block in quick metrics, but there’s no toggle or tuning surface in the main UI/docs beyond the new section.
