# XIC Productization Pulse Reports

This folder holds short, time-windowed productization status reports generated
by the `xic-productization-pulse` skill.

A pulse is a read-side synthesis. It should summarize current lane tiers,
recent evidence, blocker reasons, overclaim risks, and the next best actions.
It must not promote tiers, mutate product outputs, rerun RAW validation, or
replace the productization control plane.

Use pulse reports when the user needs a plain-language checkpoint instead of
another long handoff or diagnostic sidecar.
