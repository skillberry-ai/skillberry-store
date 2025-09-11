# skillberry-dev-common

Common development utilities and Makefile targets for SkillBerry projects.

## Makefile Features

- Cross-platform AWK detection (Windows/Unix)
- Help system with target documentation
- Git hooks setup
- Python virtual environment validation
- RITS API key and WatsonX environment checks

## Setup

Add as a git submodule to your project:
```bash
git submodule add https://github.ibm.com/blueberry/skillberry-dev-common.git
```

## Usage

Include in your project's Makefile:
```makefile
include skillberry-dev-common/.mk/common.mk
```
