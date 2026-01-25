# Taxa

Query iNaturalist regional flora data via SQL.

## Installation

```bash
pip install -e .
```

## Usage

Coming soon.

## Proof of Concept

Before building the full tool, test API performance:

```bash
# Test with a large taxon (e.g., Rosaceae family)
python scripts/poc_performance.py --taxon-id 47125 --timeout 300

# Test with smaller taxon (e.g., Quercus genus)
python scripts/poc_performance.py --taxon-id 47851 --timeout 60
```

The script will report estimated completion time to help decide if the approach scales.
