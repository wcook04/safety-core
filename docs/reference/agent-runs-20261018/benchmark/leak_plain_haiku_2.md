Request: Make the importer skip rows whose category is blank, instead of filing them under 'uncategorised'.

# leak_plain_haiku_2

## Tool calls
- `Bash: find  -type f -name "*import*" | head -20`
- `Read: tally/importer.py`
- `Edit: tally/importer.py`
- `Read: tally/importer.py`

## Tool errors

## Safety Core hook output

## git status after
```
 M tally/importer.py

```
## git log after
```
c8470a7 tally

```
## Final reply

Done! The importer now skips rows with blank categories instead of filing them under 'uncategorised'. The change:
- Extracts and normalizes the category (strip and lowercase)
- If the category is blank after normalization, increments the skipped counter and continues
- Otherwise, processes the row normally