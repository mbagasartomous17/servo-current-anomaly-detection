# Publication and data-release checklist

Before publishing a dataset, plot, benchmark result, or case study, confirm all of the following:

- [ ] The data owner has explicitly authorized the intended public use.
- [ ] Company, site, machine, controller, process, program, operator, and network identifiers are removed unless their release is authorized.
- [ ] No raw controller export, production log, robot program, CCTV, credential, IP address, or other restricted material is included.
- [ ] Dataset splits are by independent time blocks or days, not by randomly splitting adjacent samples from the same cycle.
- [ ] Ground-truth labels and event definitions are documented.
- [ ] Hyperparameters and thresholds are selected without using the final test partition.
- [ ] Synthetic and real measurements are clearly distinguished.
- [ ] FAR, POD, uncertainty intervals, latency, sample counts, and limitations are reported together.
- [ ] Negative results and failed approaches are not omitted.
- [ ] All figures can be regenerated from public inputs and versioned scripts.
