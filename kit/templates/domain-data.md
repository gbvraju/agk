# Data classification

Each data item of the product with its class (SPEC-0074 rule 7), one list line each, in the form
`<data item>: <personal|health|payment|confidential|public>`. An item is named once, and a person confirms the
classification (rule 9). `domain_model.py classify` writes them; `check_domains.py` checks the form.
