# Business rules

The business rules of one area (SPEC-0074 rule 7), one list line each, in the form
`BR-<n>: <rule>; source: <customer material|interview|code>, <where>; owner: <who>; <confirmed|inferred>`. A rule
number is unique across `docs/domain/`, a file holds at most 200 rules, and a rule is `confirmed` only after the
person's yes (rule 9). `domain_model.py rule` numbers and writes them; `domain_model.py confirm` changes only the
status word; `check_domains.py` checks the form.
