ID-CARD
ID-CARD is a Python package for standardized preprocessing, integration, and visualization of rodent water maze datasets across multiple labs/cohorts. It converts heterogeneous source files into a consistent wide-format schema, computes derived trial metrics, and provides a GUI for filtering and plotting trial-level outcomes.

What ID-CARD does
Imports and harmonizes data from multiple pipelines/cohorts (e.g., Barnes, Burke, McQuail, Rapp, Foster).
Applies shared key-based renaming/mapping so trial and metadata fields are consistent across datasets.
Builds trial-type aware wide tables (s, p, c) with standardized column naming.
Preserves and merges subject-level metadata (e.g., age, sex, genotype, source, calculated index fields).
Computes derived features such as cumulative timing and cumulative behavioral metrics.
Provides a GUI to:
filter subjects/trials/metadata,
plot trial variables vs selected time axes,
split curves by trial type and age groups,
display uncertainty bands (95% CI, SEM, or SD).
Package structure (high level)
import_scripts/ – cohort-specific import/transformation pipelines.
combined/ – cross-cohort combining and shared normalization utilities.
gui/ – interactive filtering and plotting application.
*/keys/ and combined/shared_keys/ – mapping/config files for schema harmonization.
Intended use
ID-CARD is designed for reproducible water maze data preparation and exploratory analysis, especially when combining datasets produced with different acquisition systems and naming conventions. It is suitable both for one-off preprocessing and for standardized repeated runs in analysis workflows.

"# ID-CARD" 
"# ID-CARD" 
"# ID-CARD" 
"# ID-CARD" 
"# ID-CARD" 
