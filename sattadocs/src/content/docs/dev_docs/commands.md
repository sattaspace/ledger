---
title: Commnds
description: A reference page in my new Starlight docs site.
---

## First run (creates everything, skips existing)
python manage.py billing_seed_data

### See every record being created
python manage.py billing_seed_data --verbose

#### Wipe all billing data and re-seed from scratch
python manage.py billing_seed_data --clear