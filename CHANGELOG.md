## v0.9.16 (2025-11-24)

### Refactor

- **geo**: improve place and country cleaning logic

## v0.9.15 (2025-11-23)

### Refactor

- increased timeout to 120 seconds

## v0.9.14 (2025-11-23)

### Refactor

- update cafi mtccindia

## v0.9.13 (2025-11-22)

### Refactor

- update cafi

## v0.9.12 (2025-11-21)

### Fix

- trim designation longer than 61 characters

## v0.9.11 (2025-11-21)

### Refactor

- **location**: clean and validate place names

## v0.9.10 (2025-11-19)

### Fix

- **taxon_name**: correct filter logic

## v0.9.9 (2025-11-18)

### Fix

- increase load state timeout to 180000 ms

## v0.9.8 (2025-11-17)

### Refactor

- **browser**: update navigation wait states and request params

## v0.9.7 (2025-11-17)

### Refactor

- improve browser request handling and update CiDSrc enum

## v0.9.6 (2025-11-17)

### Fix

- move contact initialization earlier in RequestManager

## v0.9.5 (2025-11-12)

### Refactor

- add contact option for user agent header

## v0.9.4 (2025-11-12)

### Refactor

- **doi**: make doi regex case‑insensitive and accept any non‑whitespace

## v0.9.3 (2025-11-11)

### Refactor

- update cafi to 0.9.5

## v0.9.2 (2025-11-11)

### Fix

- **AcronymManager**: identify ccnos in trimmed designations

### Refactor

- adjust request timeout logic

## v0.9.1 (2025-09-26)

### Fix

- correctly handle non-200 status responses

### Refactor

- update cafi for new links
- rename knacr to cafi
- wrap playwright in uv

## v0.9.0 (2025-09-26)

### Feat

- add country to location

### Refactor

- update project
- simplify wgs sequence regex
- correct version number
- remove deprecated

## v0.8.0 (2025-05-15)

### Feat

- add kingdom to ncbi

### Fix

- patch lpsn id and ncbi id before requesting the correct name
- remove redundant regex filter for ncbi names

## v0.7.4 (2025-05-12)

### Fix

- filter ncbi names
- remove redundant species names

## v0.7.3 (2025-05-12)

### Fix

- move to species in the slim version

## v0.7.2 (2025-05-12)

### Fix

- slim down species search trees

## v0.7.1 (2025-05-09)

### Fix

- improve simple search

## v0.7.0 (2025-05-09)

### Feat

- add slim version to taxa radix

## v0.6.0 (2025-05-09)

### Feat

- add two ranks to ncbi
- reduce radix size
- add taxa search

### Refactor

- generalize the radix tree

## v0.5.0 (2025-05-08)

### Feat

- add all genera report

## v0.4.0 (2025-05-08)

### Feat

- add all species method
- remove asyncio sleep

### Fix

- correct cooldown for gbif and lpsn

## v0.3.1 (2025-05-06)

### Fix

- change char to upper in comparison

### Refactor

- rename private reasonable date function
- remove redundant sampling declaration
- remove redundant container definition

## v0.3.0 (2025-05-06)

### Feat

- add extraction to manager
- add ccno search in text
- add max delay verification
- add lock release on domain on request
- add new source for data

### Fix

- correct ccno border detection
- update project because of h11
- correct float check in strings

### Refactor

- return longest acronym first
- improve acronym search
- update to newer ncbi taxonomy structure

## v0.2.1 (2025-03-05)

### Fix

- disallow cycles in history

## v0.2.0 (2025-03-05)

### Feat

- add history parser
- improve clean_empty_values_in_dict for lists and tuples

### Refactor

- update si-cu to si-dp
- add main status
- add DOI to README.md

## v0.1.0 (2025-02-16)

### Refactor

- update documentation
- update dependencies
