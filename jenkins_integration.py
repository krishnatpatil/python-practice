"""jenkins-migration.py

USAGE:
    git clone <git-repo-url>
    cd <git-repo-root-folder>
    python jenkins-migration.py

DESCRIPTION:

This script will attempt to analyze your environment and determine if you have a viable Jenkins configuration.
Jenkins configuration enables auto build of source code (jenkins build) & runs unittest cases during code commit's.

This scripts also ensures the dependent file's exists in the defined path's.

For existing Jenkins configuration display the release and version information read from the RELEASE & VERSION file,
and checks any broken configuration's.
"""

import argparse
import os
import re
from pathlib import Path

# Variable to store and share data between code blocks.
cfg = {}


def interrogate(args):
    """
    Identified current working directory, resolved "deliverable name" based on
    project name and update the cfg

    :param args: command line argument values.
    """
    cfg["pwd"] = os.getcwd()
    print("\nCurrent Directory: %s" % cfg["pwd"])

    cfg["project"] = {}
    print("Project: %s" % Path.cwd().name)
    # DELIVERABLENAME will be project folder name
    cfg["project"]["DELIVERABLENAME"] = Path.cwd().name

    cfg["project"]["name"] = args.name if args.name else Path.cwd().name
    cfg["project"]["dir"] = args.dir if args.dir else "SOURCES"

    # Project structure store files and directories which are collected from source directory
    cfg["project_structure"] = {"files": [], "dirs": []}


def check_for_module_build():
    """
    This function checks for existing Build.PL file and read VERSION, RELEASE information
    and print's on console under Old build system
    """
    if Path("Build.PL").is_file():
        with open("Build.PL", "r") as build:
            # Extract build VERSION & RELEASE
            build_info = re.search("(\d+\.\d+\.\d+)\.(\d+)", build.read())
            if build_info:
                cfg["project"]["VERSION"] = build_info.group(1)
                cfg["project"]["RELEASE"] = build_info.group(2)

        cfg["old_build_system"] = "Module::Build"
        print("\nOld Build System: " + cfg["old_build_system"])
    else:
        cfg["project"]["VERSION"] = "1.0.0"
        cfg["project"]["RELEASE"] = "1"


def check_for_makefile():
    """
    This function Checks "Makefile" exists (created by codeOn script), print the previous
    version, release & manifest information under Old build system
    """
    if Path("Makefile").is_file():
        # Makefile
        # VERSION = 1.0.0
        # RELEASE = 1
        _extract = re.compile("^(.+)=(.+)$")

        cfg["old_build_system"] = "Make"
        print("\nOld Build System: %s" % cfg["old_build_system"])

        for _file in [
            "MANIFEST",
            "VERSION",
            "RELEASE",
            "tools/MANIFEST",
            "tools/VERSION",
            "tools/RELEASE",
        ]:
            if not Path(_file).is_file():
                continue

            with open(_file) as f:
                for line in f:
                    _groups = _extract.search(line)
                    if _groups:
                        cfg["project"].update({_groups.group(1): _groups.group(2)})

        # sort and print the values collected on console.
        for key in sorted(cfg["project"], key=lambda k: k.split()[0]):
            print("  {:<20}\t\t= {:<20}".format(key, cfg["project"][key]))


def check_for_new_build_system():
    """
    This function check if CoDE scripts exists in the project directory
    The new build system is instantiated if it does not exists, create and validate.
    if exists, validate.
    """
    instantiate_new_build_system()
    interrogate_build_system()


def instantiate_new_build_system():
    """
    The new build system starts generating CoDE scripts
    """
    print(
        "\n--[Generation]-------------------------------------------------------------"
    )

    # Create folders required for new build system
    folders = ["SPECS", "SOURCES", "tools"]
    for folder in folders:
        if not Path(folder).exists():
            os.mkdir(folder)

    spec_file = "SPECS/{}.spec".format(cfg["project"]["DELIVERABLENAME"])

    generate_gitignore(".gitignore")
    generate_pylintrc(".pylintrc")
    generate_coveragerc(".coveragerc")
    generate_jenkinsfile("Jenkinsfile")
    generate_dockerfile("Dockerfile")
    generate_manifest("MANIFEST")
    generate_release("RELEASE")
    generate_version("VERSION")
    generate_makefile("Makefile")
    generate_setup_py("setup.py")
    generate_sonar("sonar-project.properties")
    generate_specs_specfile(spec_file)
    generate_tools_check_sh("tools/check.sh")
    generate_tools_build_sh("tools/build.sh")
    generate_tools_deploy_sh("tools/deploy.sh")
    generate_tools_run_tests_sh("tools/run_tests.sh")
    generate_tools_silo_repo("tools/silo.repo")
    generate_tools_test_reqs("tools/test-requirements.txt")
    generate_tools_sample_clean("tools/sample-clean.sh")
    generate_tools_sample_run("tools/sample-run.sh")
    generate_tools_sample_test("tools/sample-test.sh")
    generate_tools_sample_coverage("tools/sample-coverage.sh")
    generate_tools_sample_deploy("tools/sample-deploy.sh")
    generate_tools_sample_sign("tools/sample-sign.sh")


def generate_gitignore(file_):
    """
    Create ".gitignore" file if does not exists in project directory.
    """
    if Path(file_).is_file():
        # Return the gitignore file if already exists
        print("\tFile: {} already exists.".format(file_))
        return

    git_ignore = "\n".join(
        [
            "# Makefile builds",
            "BUILD",
            "BUILDROOT",
            "RPMS",
            "SRPMS",
            "",
            "# Compiled code",
            "*.py[cod]",
            "*.swp",
            "*.log",
            "*.rpm",
            "*.rpmmacros",
            "*.sqlite",
            "*.db",
            "*.so",
            "",
            "# Distribution",
            "*.egg",
            "*.egg-info",
            "dist/",
            "build/",
            ".venv/",
            "eggs/",
            "sdist/",
            "develop-eggs/",
            ".installed.cfg",
            "lib64/",
            "virtualenv/",
            "",
            "# Installer logs",
            "pip-log.txt",
            "",
            "# Unit test/coverage reports",
            ".coverage",
            "cover",
            "coverage*.xml",
            ".tox",
            "nosetests.xml",
            "tests/credentials.yaml",
            "results",
            "",
            "# OS",
            ".idea",
            ".DS_Store",
            "._*",
            "",
            "# IDEs",
            ".project",
            ".pydevproject",
            ".settings",
            ".metadata",
            "\n",
        ]
    )

    # If the gitignore does not exist, Open a file and write the git_ignore data.
    with open(file_, "w") as f:
        f.write(git_ignore)

    print("\tCreated: %s." % file_)


def generate_pylintrc(file_):
    """
    Create ".pylintrc" file if does not exists in project dir
    pylintrc contains the PyLint configuration information
    """
    if Path(file_).is_file():
        # Return the pylintrc file if already exists
        print("\tFile: {} already exists.".format(file_))
        return

    py_lint = "\n".join(
        [
            "# -*- mode: makefile; -*-",
            "[MASTER]",
            "",
            "# A comma-separated list of package or module names from where C extensions",
            "# may be loaded. Extensions are loading into the active Python interpreter",
            "# and may run arbitrary code",
            "extension-pkg-whitelist=",
            "",
            "# Add files or directories to the blacklist.",
            "# They should be base names, not paths",
            "ignore=CVS",
            "",
            "# Add files or directories matching the regex patterns to the blacklist.",
            "# The regex matches against base names, not paths.",
            "ignore-patterns=",
            "",
            "# Python code to execute, usually for sys.path manipulation",
            "# such as pygtk.require().",
            "#init-hook=",
            "",
            "# Use multiple processes to speed up Pylint.",
            "jobs=1",
            "",
            "# List of plugins (as comma separated values of python modules names) to load,",
            "# usually to register additional checkers.",
            "load-plugins=",
            "",
            "# Pickle collected data for later comparisons.",
            "persistent=yes",
            "",
            "# Specify a configuration file.",
            "#rcfile=",
            "",
            "# When enabled, pylint would attempt to guess common misconfiguration",
            "# and emit user-friendly hints instead of false-positive error messages",
            "suggestion-mode=yes",
            "",
            "# Allow loading of arbitrary C extensions. Extensions are imported into",
            "# the active Python interpreter and may run arbitrary code.",
            "unsafe-load-any-extension=no",
            "",
            "",
            "[MESSAGES CONTROL]",
            "",
            "# Only show warnings with the listed confidence levels. Leave empty",
            "# to show all. Valid levels: HIGH, INFERENCE, INFERENCE_FAILURE, UNDEFINED",
            "confidence=",
            "",
            "# Disable the message, report, category or checker with the given id(s). You",
            "# can either give multiple identifiers separated by comma (,) or put this",
            "# option multiple times (only on the command line, not in the configuration",
            '# file where it should appear only once).You can also use "--disable=all" to',
            "# disable everything first and then reenable specific checks. For example, if",
            '# you want to run only the similarities checker, you can use "--disable=all"',
            '# --enable=similarities". If you want to run only the classes checker, but have',
            '# no Warning level messages displayed, use "--disable=all --enable=classes',
            '# --disable=W"',
            "disable=print-statement,",
            "        parameter-unpacking,",
            "        unpacking-in-except,",
            "        old-raise-syntax,",
            "        backtick,",
            "        long-suffix,",
            "        old-ne-operator,",
            "        old-octal-literal,",
            "        import-star-module-level,",
            "        non-ascii-bytes-literal,",
            "        invalid-unicode-literal,",
            "        raw-checker-failed,",
            "        bad-inline-option,",
            "        locally-disabled,",
            "        locally-enabled,",
            "        file-ignored,",
            "        suppressed-message,",
            "        useless-suppression,",
            "        deprecated-pragma,",
            "        apply-builtin,",
            "        basestring-builtin,",
            "        buffer-builtin,",
            "        cmp-builtin,",
            "        coerce-builtin,",
            "        execfile-builtin,",
            "        file-builtin,",
            "        long-builtin,",
            "        raw_input-builtin,",
            "        reduce-builtin,",
            "        standarderror-builtin,",
            "        unicode-builtin,",
            "        xrange-builtin,",
            "        coerce-method,",
            "        delslice-method,",
            "        getslice-method,",
            "        setslice-method,",
            "        no-absolute-import,",
            "        old-division,",
            "        dict-iter-method,",
            "        dict-view-method,",
            "        next-method-called,",
            "        metaclass-assignment,",
            "        indexing-exception,",
            "        raising-string,",
            "        reload-builtin,",
            "        oct-method,",
            "        hex-method,",
            "        nonzero-method,",
            "        cmp-method,",
            "        input-builtin,",
            "        round-builtin,",
            "        intern-builtin,",
            "        unichr-builtin,",
            "        map-builtin-not-iterating,",
            "        zip-builtin-not-iterating,",
            "        range-builtin-not-iterating,",
            "        filter-builtin-not-iterating,",
            "        using-cmp-argument,",
            "        eq-without-hash,",
            "        div-method,",
            "        idiv-method,",
            "        rdiv-method,",
            "        exception-message-attribute,",
            "        invalid-str-codec,",
            "        sys-max-int,",
            "        bad-python3-import,",
            "        deprecated-string-function,",
            "        deprecated-str-translate-call,",
            "        deprecated-itertools-function,",
            "        deprecated-types-field,",
            "        next-method-defined,",
            "        dict-items-not-iterating,",
            "        dict-keys-not-iterating,",
            "        dict-values-not-iterating,",
            "        deprecated-operator-function,",
            "        deprecated-urllib-function,",
            "        xreadlines-attribute,",
            "        deprecated-sys-function,",
            "        exception-escape,",
            "        comprehension-escape,",
            "        C0326,",
            "        invalid-name,",
            "        bad-continuation,",
            "        trailing-whitespace",
            "",
            "# Enable the message, report, category or checker with the given id(s). You can",
            "# either give multiple identifier separated by comma (,) or put this option",
            "# multiple time (only on the command line, not in the configuration file where",
            '# it should appear only once). See also the "--disable" option for examples.',
            "enable=c-extension-no-member",
            "",
            "",
            "[REPORTS]",
            "",
            "# Python expression which should return a note less than 10 (10 is the highest",
            "# note). You have access to the variables errors warning, statement which",
            "# respectively contain the number of errors / warnings messages and the total",
            "# number of statements analyzed. This is used by the global evaluation report",
            "# (RP0004).",
            "evaluation=10.0 - ((float(5 * error + warning + refactor + convention) / statement) * 10)",
            "",
            "# Template used to display messages. This is a python new-style format string",
            "# used to format the message information. See doc for all details.",
            "#msg-template=",
            "",
            "# Set the output format. Available formats are text, parseable, colorized, json",
            "# and msvs (visual studio).You can also give a reporter class, eg",
            "# mypackage.mymodule.MyReporterClass.",
            "output-format=text",
            "",
            "# Tells whether to display a full report or only the messages",
            "reports=no",
            "",
            "# Activate the evaluation score.",
            "score=yes",
            "",
            "",
            "[REFACTORING]",
            "",
            "# Maximum number of nested blocks for function / method body",
            "max-nested-blocks=5",
            "",
            "# Complete name of functions that never returns. When checking for",
            "# inconsistent-return-statements if a never returning function is called then",
            "# it will be considered as an explicit return statement and no message will be",
            "# printed.",
            "never-returning-functions=optparse.Values,sys.exit",
            "",
            "",
            "[SPELLING]",
            "",
            "# Limits count of emitted suggestions for spelling mistakes",
            "max-spelling-suggestions=4",
            "",
            "# Spelling dictionary name. Available dictionaries: none. To make it working",
            "# install python-enchant package.",
            "spelling-dict=",
            "",
            "# List of comma separated words that should not be checked.",
            "spelling-ignore-words=",
            "",
            "# A path to a file that contains private dictionary; one word per line.",
            "spelling-private-dict-file=",
            "",
            "# Tells whether to store unknown words to indicated private dictionary in",
            "# --spelling-private-dict-file option instead of raising a message.",
            "spelling-store-unknown-words=no",
            "",
            "",
            "[TYPECHECK]",
            "",
            "# List of decorators that produce context managers, such as",
            "# contextlib.contextmanager. Add to this list to register other decorators that",
            "# produce valid context managers.",
            "contextmanager-decorators=contextlib.contextmanager",
            "",
            "# List of members which are set dynamically and missed by pylint inference",
            "# system, and so shouldn't trigger E1101 when accessed. Python regular",
            "# expressions are accepted.",
            "generated-members=",
            "",
            "# Tells whether missing members accessed in mixin class should be ignored. A",
            '# mixin class is detected if its name ends with "mixin" (case insensitive).',
            "ignore-mixin-members=yes",
            "",
            "# This flag controls whether pylint should warn about no-member and similar",
            "# checks whenever an opaque object is returned when inferring. The inference",
            "# can return multiple potential results while evaluating a Python object, but",
            "# some branches might not be evaluated, which results in partial inference. In",
            "# that case, it might be useful to still emit no-member and other checks for",
            "# the rest of the inferred objects.",
            "ignore-on-opaque-inference=yes",
            "",
            "# List of class names for which member attributes should not be checked (useful",
            "# for classes with dynamically set attributes). This supports the use of",
            "# qualified names.",
            "ignored-classes=optparse.Values,thread._local,_thread._local",
            "",
            "# List of module names for which member attributes should not be checked",
            "# (useful for modules/projects where namespaces are manipulated during runtime",
            "# and thus existing member attributes cannot be deduced by static analysis. It",
            "# supports qualified module names, as well as Unix pattern matching.",
            "ignored-modules=",
            "",
            "# Show a hint with possible names when a member name was not found. The aspect",
            "# of finding the hint is based on edit distance.",
            "missing-member-hint=yes",
            "",
            "# The minimum edit distance a name should have in order to be considered a",
            "# similar match for a missing member name.",
            "missing-member-hint-distance=1",
            "",
            "# The total number of similar names that should be taken in consideration when",
            "# showing a hint for a missing member.",
            "missing-member-max-choices=1",
            "",
            "",
            "[VARIABLES]",
            "",
            "# List of additional names supposed to be defined in builtins. Remember that",
            "# you should avoid to define new builtins when possible.",
            "additional-builtins=",
            "",
            "# Tells whether unused global variables should be treated as a violation.",
            "allow-global-unused-variables=yes",
            "",
            "# List of strings which can identify a callback function by name. A callback",
            "# name must start or end with one of those strings.",
            "callbacks=cb_,",
            "          _cb",
            "",
            "# A regular expression matching the name of dummy variables (i.e. expectedly",
            "# not used).",
            "dummy-variables-rgx=_+$|(_[a-zA-Z0-9_]*[a-zA-Z0-9]+?$)|dummy|^ignored_|^unused_",
            "",
            "# Argument names that match this expression will be ignored. Default to name",
            "# with leading underscore",
            "ignored-argument-names=_.*|^ignored_|^unused_",
            "",
            "# Tells whether we should check for unused import in __init__ files.",
            "init-import=no",
            "",
            "# List of qualified module names which can have objects that can redefine",
            "# builtins.",
            "redefining-builtins-modules=six.moves,past.builtins,future.builtins,io,builtins",
            "",
            "",
            "[FORMAT]",
            "",
            "# Expected format of line ending, e.g. empty (any line ending), LF or CRLF.",
            "expected-line-ending-format=",
            "",
            "# Regexp for a line that is allowed to be longer than the limit.",
            "ignore-long-lines=^\s*(# )?<?https?://\S+>?$",
            "",
            "# Number of spaces of indent required inside a hanging or continued line.",
            "indent-after-paren=4",
            "",
            '# String used as indentation unit. This is usually "    " (4 spaces) or "\t" (1',
            "# tab).",
            "indent-string='    '",
            "",
            "# Maximum number of characters on a single line.",
            "max-line-length=120",
            "",
            "# Maximum number of lines in a module",
            "max-module-lines=1000",
            "",
            "# List of optional constructs for which whitespace checking is disabled. `dict-",
            "# separator` is used to allow tabulation in dicts, etc.: {1  : 1,\n222: 2}.",
            "# `trailing-comma` allows a space between comma and closing bracket: (a, ).",
            "# `empty-line` allows space-only lines.",
            "no-space-check=trailing-comma,",
            "               dict-separator",
            "",
            "# Allow the body of a class to be on the same line as the declaration if body",
            "# contains single statement.",
            "single-line-class-stmt=no",
            "",
            "# Allow the body of an if to be on the same line as the test if there is no",
            "# else.",
            "single-line-if-stmt=no",
            "",
            "",
            "[SIMILARITIES]",
            "",
            "# Ignore comments when computing similarities.",
            "ignore-comments=yes",
            "",
            "# Ignore docstrings when computing similarities.",
            "ignore-docstrings=yes",
            "",
            "# Ignore imports when computing similarities.",
            "ignore-imports=no",
            "",
            "# Minimum lines number of a similarity.",
            "min-similarity-lines=4",
            "",
            "",
            "[BASIC]",
            "",
            "# Naming style matching correct argument names",
            "argument-naming-style=camelCase",
            "",
            "# Regular expression matching correct argument names. Overrides argument-",
            "# naming-style",
            "#argument-rgx=",
            "",
            "# Naming style matching correct attribute names",
            "attr-naming-style=camelCase",
            "",
            "# Regular expression matching correct attribute names. Overrides attr-naming-",
            "# style",
            "#attr-rgx=",
            "",
            "# Bad variable names which should always be refused, separated by a comma",
            "bad-names=foo,",
            "          bar,",
            "          baz,",
            "          toto,",
            "          tutu,",
            "          tata",
            "",
            "# Naming style matching correct class attribute names",
            "class-attribute-naming-style=any",
            "",
            "# Regular expression matching correct class attribute names. Overrides class-",
            "# attribute-naming-style",
            "#class-attribute-rgx=",
            "",
            "# Naming style matching correct class names",
            "class-naming-style=PascalCase",
            "",
            "# Regular expression matching correct class names. Overrides class-naming-style",
            "#class-rgx=",
            "",
            "# Naming style matching correct constant names",
            "const-naming-style=UPPER_CASE",
            "",
            "# Regular expression matching correct constant names. Overrides const-naming-",
            "# style",
            "#const-rgx=",
            "",
            "# Minimum line length for functions/classes that require docstrings, shorter",
            "# ones are exempt.",
            "docstring-min-length=-1",
            "",
            "# Naming style matching correct function names",
            "function-naming-style=camelCase",
            "",
            "# Regular expression matching correct function names. Overrides function-",
            "# naming-style",
            "#function-rgx=",
            "",
            "# Good variable names which should always be accepted, separated by a comma",
            "good-names=i,",
            "           j,",
            "           k,",
            "           ex,",
            "           run,",
            "           _",
            "",
            "# Include a hint for the correct naming format with invalid-name",
            "include-naming-hint=no",
            "",
            "# Naming style matching correct inline iteration names",
            "inlinevar-naming-style=any",
            "",
            "# Regular expression matching correct inline iteration names. Overrides",
            "# inlinevar-naming-style",
            "#inlinevar-rgx=",
            "",
            "# Naming style matching correct method names",
            "method-naming-style=camelCase",
            "",
            "# Regular expression matching correct method names. Overrides method-naming-",
            "# style",
            "#method-rgx=",
            "",
            "# Naming style matching correct module names",
            "module-naming-style=any",
            "",
            "# Regular expression matching correct module names. Overrides module-naming-",
            "# style",
            "#module-rgx=",
            "",
            "# Colon-delimited sets of names that determine each other's naming style when",
            "# the name regexes allow several styles.",
            "name-group=",
            "",
            "# Regular expression which should only match function or class names that do",
            "# not require a docstring.",
            "no-docstring-rgx=^_",
            "",
            "# List of decorators that produce properties, such as abc.abstractproperty. Add",
            "# to this list to register other decorators that produce valid properties.",
            "property-classes=abc.abstractproperty",
            "",
            "# Naming style matching correct variable names",
            "variable-naming-style=camelCase",
            "",
            "# Regular expression matching correct variable names. Overrides variable-",
            "# naming-style",
            "#variable-rgx=",
            "",
            "",
            "[LOGGING]",
            "",
            "# Logging modules to check that the string format arguments are in logging",
            "# function parameter format",
            "logging-modules=logging",
            "",
            "",
            "[MISCELLANEOUS]",
            "",
            "# List of note tags to take in consideration, separated by a comma.",
            "notes=FIXME,",
            "      XXX,",
            "      TODO",
            "",
            "",
            "[IMPORTS]",
            "",
            "# Allow wildcard imports from modules that define __all__.",
            "allow-wildcard-with-all=no",
            "",
            "# Analyse import fallback blocks. This can be used to support both Python 2 and",
            "# 3 compatible code, which means that the block might have code that exists",
            "# only in one or another interpreter, leading to false positives when analysed.",
            "analyse-fallback-blocks=no",
            "",
            "# Deprecated modules which should not be used, separated by a comma",
            "deprecated-modules=regsub,",
            "                   TERMIOS,",
            "                   Bastion,",
            "                   rexec",
            "",
            "# Create a graph of external dependencies in the given file (report RP0402 must",
            "# not be disabled)",
            "ext-import-graph=",
            "",
            "# Create a graph of every (i.e. internal and external) dependencies in the",
            "# given file (report RP0402 must not be disabled)",
            "import-graph=",
            "",
            "# Create a graph of internal dependencies in the given file (report RP0402 must",
            "# not be disabled)",
            "int-import-graph=",
            "",
            "# Force import order to recognize a module as part of the standard",
            "# compatibility libraries.",
            "known-standard-library=",
            "",
            "# Force import order to recognize a module as part of a third party library.",
            "known-third-party=enchant",
            "",
            "",
            "[DESIGN]",
            "",
            "# Maximum number of arguments for function / method",
            "max-args=15",
            "",
            "# Maximum number of attributes for a class (see R0902).",
            "max-attributes=20",
            "",
            "# Maximum number of boolean expressions in a if statement",
            "max-bool-expr=10",
            "",
            "# Maximum number of branch for function / method body",
            "max-branches=20",
            "",
            "# Maximum number of locals for function / method body",
            "max-locals=30",
            "",
            "# Maximum number of parents for a class (see R0901).",
            "max-parents=10",
            "",
            "# Maximum number of public methods for a class (see R0904).",
            "max-public-methods=100",
            "",
            "# Maximum number of return / yield for function / method body",
            "max-returns=10",
            "",
            "# Maximum number of statements in function / method body",
            "max-statements=80",
            "",
            "# Minimum number of public methods for a class (see R0903).",
            "min-public-methods=0",
            "",
            "",
            "[CLASSES]",
            "",
            "# List of method names used to declare (i.e. assign) instance attributes.",
            "defining-attr-methods=__init__,",
            "                      __new__,",
            "                      setUp",
            "",
            "# List of member names, which should be excluded from the protected access",
            "# warning.",
            "exclude-protected=_asdict,",
            "                  _fields,",
            "                  _replace,",
            "                  _source,",
            "                  _make",
            "",
            "# List of valid names for the first argument in a class method.",
            "valid-classmethod-first-arg=cls",
            "",
            "# List of valid names for the first argument in a metaclass class method.",
            "valid-metaclass-classmethod-first-arg=mcs",
            "",
            "",
            "[EXCEPTIONS]",
            "",
            "# Exceptions that will emit a warning when being caught. Defaults to",
            '# "Exception"',
            "overgeneral-exceptions=Exception",
            "\n",
        ]
    )

    # If the py_lint does not exist, Open a file and write the py_lint.
    with open(file_, "w") as f:
        f.write(py_lint)

    print("\tCreated: %s." % file_)


def generate_coveragerc(file_):
    """
    This function creates the "coveragerc" if it does not exist in new build system.
    """
    if Path(file_).is_file():
        # Return the coveragerc file if already exists
        print("\tFile: {} already exists.".format(file_))
        return

    coverage = "\n".join(["[run]", "include =", "    {project_dir}/*", "\n",])

    # If the coveragerc does not exist, Open a file and write the coveragerc.
    with open(file_, "w") as f:
        f.write(coverage.format(project_dir=cfg["project"]["dir"]))

    print("\tCreated: %s." % file_)


def generate_jenkinsfile(file_):
    """
    Create "Jenkinsfile" if does not exists in the project directory.
    It contains information about pipeline stages.

    :param file_:
    """
    if Path(file_).is_file():
        # Return the Jenkinsfile if already exists
        print("\tFile: {} already exists.".format(file_))
        return

    pipeline_data = "\n".join(
        [
            "pipeline {",
            "    agent none",
            "    stages {",
            "        stage('Test') {",
            "            agent {",
            "                dockerfile {",
            '                    filename "Dockerfile"',
            "                }",
            "            }",
            "            steps {",
            "                withConjurCredentials([",
            "                    conEnv: 'prod',",
            "                    hostPath: 'host/it/monitoring/apikey',",
            "                    jenkinsCredentialsId: 'APP_PROD_API_KEY',",
            "                    variableIds: 'app:variable:it/monitoring/credentials/prod/silo_assurance/silo_assurance,app:variable:it/monitoring/credentials/prod/silo_api.gen/silo_api.gen,app:variable:it/monitoring/credentials/prod/test_app.gen/test_app.gen',",
            "                ]) {",
            '                     sh "tools/check.sh"',
            "                }",
            "            }",
            "        }",
            "        stage('Sonar') {",
            "            agent any",
            "            steps {",
            '                sonarScan(sonarServer: "Sonar")',
            "            }",
            "        }",
            "        stage('Build') {",
            "            agent {",
            "                docker {",
            '                    image "containers.app.com/gissdlc/build_check_centos7"',
            "                }",
            "            }",
            "            when {",
            '                branch "master"',
            "            }",
            "            steps {",
            '                sh "tools/build.sh"',
            "            }",
            "        }",
            "        stage('Deploy') {",
            "            agent any",
            "            when {",
            '                branch "master"',
            "            }",
            "            steps {",
            '                sh "tools/deploy.sh"',
            "            }",
            "        }",
            "    }",
            "}",
            "\n",
        ]
    )

    # If the Jenkinsfile does not exist, Open a file and write the pipeline data.
    with open(file_, "w") as f:
        f.write(pipeline_data)

    print("\tCreated: %s." % file_)


def generate_dockerfile(file_):
    """
    This function creates the "Dockerfile" if it does not exist in new build system.
    It contains the docker configuration to run the container.
    """
    if Path(file_).is_file():
        # Return the Dockerfile if already exists
        print("\tFile: {} already exists.".format(file_))
        return

    docker_config = "\n".join(
        [
            "FROM docker.hub.com/alpine",
            "",
            "# Maintainer",
            'LABEL maintainer="test@example.com"',
            "",
            "USER root",
            "",
            "# Create required users, groups and directories",
            "RUN groupadd test                                                   && \\",
            "    useradd -g test test                                            && \\",
            "    mkdir /apps .pylint.d                                           && \\",
            "    chmod -R 777 /apps .pylint.d",
            "",
            "# Copy required files to the container",
            "COPY tools/silo.repo tools/test-requirements.txt /apps/",
            "",
            "# Install dependency packages",
            "RUN yum install -y mariadb103-devel unixODBC-devel openldap-devel    && \\",
            "    yum install -c /apps/silo.repo -y python_2_7_14    && \\",
            "    pip install -r /apps/test-requirements.txt",
            "\n",
        ]
    )

    # If the Dockerfile does not exist, Open a file and write the docker_config data.
    with open(file_, "w") as f:
        f.write(docker_config)

    print("\tCreated: %s." % file_)


def generate_manifest(file_):
    """
    This function creates the " MANIFEST file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        print("\tFile: {} already exists.".format(file_))
        return

    coverage = "\n".join(
        [
            "DELIVERABLENAME={project_name}",
            "RPMNAME={project_name}",
            "RPMDIR=.",
            "BUILDSRC=false",
            "ARCH=noarch",
            "ROLE=role",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(coverage.format(project_name=cfg["project"]["name"]))

    print("\tCreated: %s." % file_)


def generate_release(file_):
    """
    This function creates the "RELEASE file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        print("\tFile: {} already exists.".format(file_))
        return

    release = "\n".join(["RELEASE=1", "\n",])

    with open(file_, "w") as f:
        f.write(release)

    print("\tCreated: %s." % file_)


def generate_version(file_):
    """
    This function creates the "VERSION file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        print("\tFile: {} already exists.".format(file_))
        return

    version = "\n".join(["VERSION=1.0.0", "\n",])

    with open(file_, "w") as f:
        f.write(version)

    print("\tCreated: %s." % file_)


def generate_makefile(file_):
    """
    This function creates the "Make file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        # Return the makefile file if already exists
        print("\tFile: {} already exists.".format(file_))
        return

    make_file = "\n".join(
        [
            "#----------------------------------------------------------------------",
            "# NAME:",
            "#	Makefile",
            "#",
            "# USAGE:",
            "#	make		## all == realclean + rpmbuild + clean",
            "#	make check	## Run CoDE check manually - heighliner check (equivalent) - Suitable for Jenkins + SonarQube + CDAnalytics",
            "#	make coverage	## Run test suite with HTML code coverage",
            "#	make run	## Run from this build directory (if appropriate)",
            "#	make test	## Run test suite without code coverage",
            "#	make sign	## Sign the RPM",
            "#	make deploy	## upload RPM to target yum repos (up to 4 roles)",
            "#	make clean	## Clean all artifacts except the RPM.",
            "#	make realclean	## Clean ALL artifacts, including the RPM.",
            "#",
            "# DESCRIPTION:",
            "#	Clarify App vs CoDE build scripts by using the .PHONY tags",
            "",
            "include MANIFEST",
            "include VERSION",
            "include RELEASE",
            "",
            "FILES = \\",
            "",
            ".PHONY: CoDE App",
            "",
            "all: realclean rpmbuild clean",
            "",
            "rpmbuild: App",
            "	cd `pwd`; rpmbuild --buildroot `pwd`/BUILDROOT/$(RPMNAME) \\",
            '		--define "_topdir `pwd`" \\',
            "		-vv -ba `pwd`/SPECS/$(RPMNAME).spec \\",
            '		--define "RPMNAME $(RPMNAME)" \\',
            '		--define "DELIVERABLENAME $(DELIVERABLENAME)" \\',
            '		--define "RPMDIR /" \\',
            '		--define "BUILDSRC false" \\',
            '		--define "ARCH ${ARCH}" \\',
            '		--define "VERSION $(VERSION)" \\',
            '		--define "RELEASE $(RELEASE)"',
            "	cp `pwd`/RPMS/${ARCH}/*.rpm .",
            "",
            "check: CoDE",
            "	cd `pwd`; sh tools/check.sh",
            "",
            "run: App",
            "	cd `pwd`; sh tools/sample-run.sh ${RPMNAME}-${VERSION}-${RELEASE}.${ARCH}.rpm",
            "",
            "test: App",
            "	cd `pwd`; sh tools/sample-test.sh ${RPMNAME}-${VERSION}-${RELEASE}.${ARCH}.rpm",
            "",
            "coverage: App",
            "	cd `pwd`; sh tools/sample-coverage.sh ${RPMNAME}-${VERSION}-${RELEASE}.${ARCH}.rpm",
            "",
            "deploy: App",
            "	cd `pwd`; sh tools/sample-deploy.sh $(ROLE) $(ROLE2) $(ROLE3) $(ROLE4)",
            "",
            "sign: App",
            "	cd `pwd`; sh tools/sample-sign.sh $(RPMDIR)/$(RPMNAME)-$(VERSION)-$(RELEASE).$(ARCH).rpm",
            "",
            "clean: App",
            "	cd `pwd`; sh tools/sample-clean.sh",
            "",
            "realclean: App",
            "	cd `pwd`; sh tools/sample-clean.sh realclean",
            "\n",
        ]
    )

    # If the makefile does not exist, Open a file and write the makefile.
    with open(file_, "w") as f:
        f.write(make_file)

    print("\tCreated: %s." % file_)


def generate_setup_py(file_):
    """
    This function creates the ".setup file" if it does not exist in new build system.
    """
    if Path(file_).is_file():
        # Return the setup_py file if already exists
        print("\tFile: {} already exists.".format(file_))
        return

    setup_py = "\n".join(
        [
            "from setuptools import setup, find_packages",
            "",
            "setup(",
            "    name='{project_name}',",
            "    version='1.0.0.1',",
            "    python_requires='>=2.7',",
            "    description='describe your build here...',",
            "    author='{env_user}',",
            '    author_email="test@example.com",',
            "    packages=find_packages(),",
            "    include_package_data=True,",
            "    install_requires=[",
            "    ],",
            ")",
            "\n",
        ]
    )

    # If the setup_py does not exist, Open a file and write the setup_py data.
    with open(file_, "w") as f:
        f.write(
            setup_py.format(
                project_name=cfg["project"]["name"], env_user=os.getenv("USER", "root")
            )
        )

    print("\tCreated: %s." % file_)


def generate_sonar(file_):
    """
    This function creates the "sonar file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        print("\tFile: {} already exists.".format(file_))
        return

    coverage = "\n".join(
        [
            "sonar.projectKey={project_name}:python",
            "sonar.projectName={project_name}",
            "sonar.projectVersion={makefile}",
            "sonar.language=py",
            "sonar.sourceEncoding=UTF-8",
            "sonar.python.coverage.reportPaths=results/coverage.xml",
            "sonar.tests={project_dir}/tests/",
            "sonar.python.xunit.reportPath=results/test-results.xml",
            "sonar.sources={project_dir}/scripts",
            "sonar.exclusions=**/*.cfg,**/*.ini,**/*.pyc,**./*.sh,**./*.pl,**/tests/**,**/configs/**,**/crons/**",
            "sonar.python.coveragePlugin=cobertura",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(
            coverage.format(
                project_name=cfg["project"]["name"],
                project_dir=cfg["project"]["dir"],
                makefile=cfg["project"]["VERSION"] + "." + cfg["project"]["RELEASE"],
            )
        )

    print("\tCreated: %s." % file_)


def generate_specs_specfile(file_):
    """
    Create specs file based on deliverable-name
    """
    print("\n--[generate SPECS specfile()]-------------------------------------------")

    if scan_project_structure():
        if Path(file_).is_file():
            print("\tFile: %s already exists." % file_)
            return

        specs = [
            "%define __jar_repack %{nil}",
            "%define scripts_deploy_dir <script_deploy_directory_path>",
            "%define scripts_deploy_group test",
            "%define scripts_deploy_user test",
            "%define crons_deploy_dir /etc/cron.d",
            "%define crons_deploy_group root",
            "%define crons_deploy_user root",
            "%define configs_deploy_dir <config_file_deploy_directory_path>",
            "%define configs_deploy_group test",
            "%define configs_deploy_user test",
            "%define logs_deploy_dir <log_file_deploy_directory_path>",
            "%define logs_deploy_group test",
            "%define logs_deploy_user test",
            "%define init_deploy_dir /etc/init.d",
            "%define init_deploy_group root",
            "%define init_deploy_user root",
            "",
            "Summary:    %{DELIVERABLENAME}",
            "Name:       %{RPMNAME}",
            "Version:    %{VERSION}",
            "Release:    %{RELEASE}",
            "Group:      TEST",
            "License:    Copyright Test Systems. 2022",
            "",
            "BuildRoot:  %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)",
            "BuildArch:  %{ARCH}",
            "AutoReqProv: no",
            "",
            "Requires: python_2_7_14",
            "",
            emit_specfile_provides(),
            "",
            "%description",
            "BUILD: {DELIVERABLENAME}".format(
                DELIVERABLENAME=cfg["project"]["DELIVERABLENAME"]
            ),
            "",
            "$Id$",
            "",
            "%prep",
            "",
            "%build",
            "",
            "%install",
            emit_specfile_install_files(),
            "",
            "%clean",
            "rm -rf %{buildroot}",
            "",
            "%files",
            emit_specfile_files(),
            "",
            "%post",
            "",
            "%preun",
            "",
            "%postun",
            "",
            "%changelog",
            "\n",
        ]
        with open(file_, "w") as f:
            f.write("\n".join(specs))

        print("\tCreated: %s" % file_)
    else:
        print("\tscan_project_structure() returned 0")


def scan_project_structure():
    """
    Scan the existing project structure recursively for files and directories to be added in specs file.

    :return: 0 if Makefile does not exists and 1 if exists.
    """
    ret_val = 0
    if Path("Makefile").is_file():
        ret_val = 1
        print(
            "\tRESTRUCTURING YOUR TREE. If you need to do this by hand, remove this working directory and recheckout."
        )
        print("\t\tcd ..")
        print("\t\trm -rf %s" % cfg["project"]["DELIVERABLENAME"])

        # print git repository url from where the project was cloned.
        if Path(".git/config").is_file():
            with open(".git/config") as f:
                search = re.search("url = (.+)", f.read())
                if search:
                    print("\t\tgit clone " + search.group(1))

        print("\t\tcd " + cfg["project"]["DELIVERABLENAME"])

        # Create source directory and give executable permission.
        if not Path("SOURCES").exists():
            print("\tCreating SOURCES...")
            os.mkdir("SOURCES", mode=0o775)

        if not Path("README.md").exists():
            print("\n\tCreating README...")
            open("README.md", "a").close()
            os.chmod("README.md", 0o775)

        # Refactoring the project as per CoDE standard.
        for entry in os.listdir("."):
            if Path(entry).is_dir():
                # Skip this files from refactoring
                if re.search("^(SPECS|tools|SOURCES|TESTS|testsuites|\..+)", entry):
                    if entry == "testsuites":
                        print(
                            "\tNOT moving testsuites, but you should move your files to SOURCES/tests for consistency..."
                        )
                elif re.search("home|apps", entry):
                    print("\tMoving {entry}\t=> SOURCES/{entry}...".format(entry=entry))
                    os.system("git mv {entry} SOURCES/{entry}".format(entry=entry))

        # traverse through project source folder.
        recurse("SOURCES")

    return ret_val


def recurse(root, sub_dir=""):
    """
    Recursively traverse through the root directory to identify folders and files
    available in the project root directory and update to "cfg" (global variable)

    :param root:
    :param sub_dir:
    :return:
    """
    dir_path = str(Path(root, sub_dir))
    for entry in sorted(os.listdir(dir_path)):
        path_ = str(Path(root, sub_dir, entry))

        if Path(path_).is_file():
            cfg["project_structure"]["files"].append(path_)
        elif Path(path_).is_dir():
            cfg["project_structure"]["dirs"].append(path_)
            # if directory traverse.
            recurse(root, str(Path(sub_dir, entry)))


def emit_specfile_provides():
    """
    Generate formatted string based on files collected from project source dir
    :return:
    """
    files = [
        "Provides: " + file_.split("/")[-1]
        for file_ in sorted(cfg["project_structure"]["files"])
        if file_
    ]
    return "\n".join(files)


def emit_specfile_install_files():
    """
    Generate formatted string based on files collected from project source dir
    :return:
    """
    files = [
        "install -D -m 775 %_sourcedir/{file} %{{buildroot}}/{file}".format(file=file_)
        for file_ in sorted(cfg["project_structure"]["files"])
        if file_
    ]
    return "\n".join(files)


def emit_specfile_files():
    """
    Generate formatted string based on files collected from project source dir
    :return:
    """
    files = ["/" + file_ for file_ in sorted(cfg["project_structure"]["files"])]
    return "\n".join(files)


def generate_tools_check_sh(file_):
    """
    This function creates the "check.sh file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\n\tFile: {} already exists.".format(file_))
        return

    sh_file = "\n".join(
        [
            "#!/usr/bin/env bash",
            "#--------------------------------------------------------------------------------------------",
            "# NAME:",
            "#    tools/check.sh",
            "#",
            "# DESCRIPTION:",
            "#    Check script which performs basic testing.",
            "#",
            "# NEXT STEPS:",
            "#    tools/build.sh",
            "#",
            "",
            'echo "--[CoDE]--[check.sh]------------------------------------------------------------------"',
            "set -e",
            "",
            'echo "--[CWD]-------------------------------------------------------------------------------"',
            "pwd",
            "",
            'echo "--[id]--------------------------------------------------------------------------------"',
            "id",
            "",
            'echo "--[env]-------------------------------------------------------------------------------"',
            "env | sort",
            "",
            'echo "--[ls -ltr]---------------------------------------------------------------------------"',
            "ls -ltr",
            "",
            "# need to add the python_2_7_14 path to the default python import path",
            "export PATH=$PATH:/apps/Python-2.7.14/bin",
            "export PYTHONPATH=$PYTHONPATH:/apps/Python-2.7.14/lib/python2.7",
            "",
            "# Running pylint",
            'echo "--[run_tests.sh]--[pylint]------------------------------------------------------------"',
            "./tools/run_tests.sh -l",
            "",
            "# Running Unit Tests",
            'echo "--[run_tests.sh]--[unit tests]--------------------------------------------------------"',
            "./tools/run_tests.sh -u",
            "",
            'echo "--[cat results/coverage.xml]----------------------------------------------------------"',
            "cat results/coverage.xml",
            'echo "--[cat results/test-results.xml]------------------------------------------------------"',
            "cat results/test-results.xml",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sh_file)

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)

    print("\n\tCreated: %s." % file_)


def generate_tools_build_sh(file_):
    """
    This function creates the "build.sh file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    sh_file = "\n".join(
        [
            "#!/usr/bin/env bash",
            "#--------------------------------------------------------------------------------------------",
            "# NAME:",
            "#    tools/build.sh",
            "#",
            "# DESCRIPTION:",
            "#    Build script which produces a RPM via Makefile.",
            "#",
            "# NEXT STEPS:",
            "#    tools/deploy.sh",
            "",
            'echo "--[CoDE]--[build.sh]------------------------------------------------------------------"',
            "set -e",
            "",
            'echo "--[CWD]-------------------------------------------------------------------------------"',
            "pwd",
            "",
            'echo "--[ls -ltra]----------------------------------------------------------------------------"',
            "ls -ltra",
            "",
            'echo "--[make all]---------------------------------------------------------------------------"',
            "make",
            "",
            'echo "--[ls -l *.rpm]-----------------------------------------------------------------------"',
            "ls -l *.rpm",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sh_file)

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)

    print("\tCreated: %s." % file_)


def generate_tools_deploy_sh(file_):
    """
    This function creates the "deploy.sh file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    sh_file = "\n".join(
        [
            "#!/usr/bin/env bash",
            "#--------------------------------------------------------------------------------------------",
            "# NAME:",
            "#    tools/deploy.sh",
            "#",
            "# DESCRIPTION:",
            "#    Deploy script to deploy the RPM to the targeted server_role-$ROLE",
            "#    yum repos.",
            "#",
            "",
            'echo "--[CoDE]--[deploy.sh]-----------------------------------------------------------------"',
            "set -e",
            "",
            'echo "Nothing to deploy..."',
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sh_file)

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)

    print("\tCreated: %s." % file_)


def generate_tools_run_tests_sh(file_):
    """
    This function creates the "run_tests.sh file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    sh_file = "\n".join(
        [
            "MODULE={project_dir}/scripts",
            "TEST_DIR_BASE={project_dir}/tests",
            "TEST_DIR_RELATIVE=./$TEST_DIR_BASE",
            "TEST_CASES=$TEST_DIR_RELATIVE/test_*",
            "COV_REPORT=results/coverage.xml",
            "UNIT_REPORT=results/test-results.xml",
            "TEST_CONFIG=TestServiceConfig.txt",
            "",
            "help(){{",
            '    echo "Usage: $0 [OPTION]..."',
            '    echo "  -h, --help         Show this help output"',
            '    echo "  -p, --pep8         Run pep8 checks"',
            '    echo "  -l, --lint         Run pylint checks and some extra custom style checks"',
            '    echo "  -u, --unit         Run unit tests"',
            '    echo "  -pl, --pl          Run pep8 and pylint checks"',
            '    echo "  --no-coverage      Don\'t make a unit test coverage report"',
            '    echo ""',
            "    exit 0;",
            "}}",
            "",
            "fail(){{",
            '    echo "FAILURE"',
            '    echo -e "$1"',
            "    exit 1;",
            "}}",
            "",
            "run_python_tests(){{",
            "    if [ -d results ]; then",
            "        rm -rf results",
            "    fi",
            "",
            "    mkdir results",
            "",
            "    # load credentials into test config file",
            '    echo "Loading credentials from Jenkins environment to TestServiceConfig.txt"',
            '    echo "[DEFAULT_SETTINGS]" > $TEST_CONFIG',
            '    echo "dbuser = silo_assurance" >> $TEST_CONFIG',
            '    echo "apiuser = silo_api.gen" >> $TEST_CONFIG',
            '    echo "snowuser = test_api.gen" >> $TEST_CONFIG',
            '    echo "snowlifecycle = production" >> $TEST_CONFIG',
            '    echo "dbpassword = ${{SECRET_MONITORING_SILO_ASSURANCE}}" >> $TEST_CONFIG',
            '    echo "apipassword = $(perl -le \'print $ENV{{"SECRET_MONITORING_SILO_API.GEN"}}\')" >> $TEST_CONFIG',
            '    echo "snowpassword = $(perl -le \'print $ENV{{"TEST_ESP.GEN"}}\')" >> $TEST_CONFIG',
            "",
            "    pytest -vv --cov=. --cov-report term-missing --junit-xml=$UNIT_REPORT --cov-report xml:$COV_REPORT $TEST_DIR_BASE",
            "    TEST_RESULT=$?",
            "",
            "    if [ $TEST_RESULT -gt 0 ]; then",
            "        exit $TEST_RESULT;",
            "    fi",
            "}}",
            "",
            "run_unit_tests(){{",
            '    echo "************** Running unit tests *********************************"',
            '    run_python_tests "unit"',
            "}}",
            "",
            "run_pep8_check(){{",
            '    echo "************** Running pep8 checks ********************************"',
            "    pycodestyle $MODULE --max-line-length=120",
            '    echo "SUCCESS"',
            "}}",
            "",
            "run_lint_check(){{",
            '    echo "************** Running pylint checks ******************************"',
            '    pylint $MODULE --rcfile=".pylintrc"',
            '    echo "SUCCESS"',
            "}}",
            "",
            "# Determine script behavior based on passed options",
            "# default behavior",
            "just_pep8=0",
            "just_lint=0",
            "just_unit=0",
            'testargs=""',
            "include_coverage=1",
            "all_style_checks=0",
            "",
            'while [ "$#" -gt 0 ]; do',
            '    case "$1" in',
            "        -h|--help) shift; help;;",
            "        -p|--pep8) shift; just_pep8=1;;",
            "        -l|--lint) shift; just_lint=1;;",
            "        -u|--unit) shift; just_unit=1;;",
            "        -pl|--pl) shift; all_style_checks=1;;",
            '        *) testargs="$testargs $1"; shift;',
            "    esac",
            "done",
            "",
            "if [ $just_unit -eq 1 ]; then",
            "    run_unit_tests",
            "    exit $?",
            "fi",
            "",
            "if [ $just_pep8 -eq 1 ]; then",
            "    run_pep8_check",
            "    exit $?",
            "fi",
            "",
            "if [ $just_lint -eq 1 ]; then",
            "    run_lint_check",
            "    exit $?",
            "fi",
            "",
            "if [ $all_style_checks -eq 1 ]; then",
            "    run_pep8_check",
            "    run_lint_check",
            "    exit $?",
            "fi",
            "",
            "run_unit_tests || exit",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sh_file.format(project_dir=cfg["project"]["dir"]))

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)

    print("\tCreated: %s." % file_)


def generate_tools_silo_repo(file_):
    """
    This function creates "silo.repo" file if it does not exist in new build system
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    silo_repo = "\n".join(
        [
            "[SILO-repository]",
            "name=App IT - Base packages - $basearch",
            "baseurl=http://eir-yum-bootstrap.test.com/yum/SILO/production/SLA/RPMS",
            "enabled=yes",
            "gpgcheck=0",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(silo_repo)

    os.chmod(file_, 0o775)

    print("\tCreated: %s." % file_)


def generate_tools_test_reqs(file_):
    """
    This function creates the "test-requirement file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    rqr_txt = "\n".join(
        [
            "pytest",
            "pytest-cov",
            "pytest-mock",
            "pylint",
            "pep8",
            "flake8",
            "coverage",
            "configparser",
            "pathlib2",
            "pathlib",
            "mysqlclient",
            "xmltodict",
            "requests",
            "pymemcache",
            "pycrypto",
            "hvac",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(rqr_txt)

    os.chmod(file_, 0o775)

    print("\tCreated: %s." % file_)


def generate_tools_sample_clean(file_):
    """
    This function creates the "sample_clean.sh file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    sample_clean = "\n".join(
        [
            "#!/usr/bin/env bash",
            "#----------------------------------------------------------------------------------------",
            "# NAME:",
            "#    tools/sample-clean.sh",
            "#",
            "# USAGE:",
            "#    cd `pwd`; sh tools/sample-clean.sh",
            "#    cd `pwd`; sh tools/sample-clean.sh realclean",
            "#",
            "# DESCRIPTION:",
            "#    Clean the normal things (first use case).",
            "#    Include the generated RPM (second use case).",
            "#",
            "",
            "rm -rf BUILD BUILDROOT RPMS SRPMS",
            "rm -rf .pytest_cache {project_dir}/tests/__pycache__ cov_html .coverage {project_dir}/tests/.coverage results",
            "",
            'if  [ "$1" = "realclean" ]; then',
            '    find . -name "*.rpm*" -exec /bin/rm {{}} \\;',
            "fi",
            "",
            'echo "---------------------------------------------------------------------------------"',
            "git status",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sample_clean.format(project_dir=cfg["project"]["dir"]))

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)
    print("\tCreated: %s." % file_)


def generate_tools_sample_run(file_):
    """
    This function creates the "run file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    sample_run = "\n".join(
        [
            "#!/usr/bin/env bash",
            "#--------------------------------------------------------------------------------------",
            "# NAME:",
            "#     tools/sample-run.sh",
            "#",
            "# DESCRIPTION:",
            "#    Modify to run your application from the build tree.",
            "#",
            "",
            "cd {project_dir}/scripts",
            "",
            "#python your_script.py args",
            "",
            "cd ../..",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sample_run.format(project_dir=cfg["project"]["dir"]))

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)
    print("\tCreated: %s." % file_)


def generate_tools_sample_test(file_):
    """
    This function creates the "test file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    sample_test = "\n".join(
        [
            "#!/usr/bin/env bash",
            "#-------------------------------------------------------------------------------------",
            "# NAME:",
            "#    tools/sample-test.sh",
            "#",
            "# DESCRIPTION:",
            "#    Run python test scripts.",
            "#",
            "",
            "RPM=$1",
            "rpm -q --filesbypkg -p $RPM",
            "",
            "pytest -vv {project_dir}/tests",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sample_test.format(project_dir=cfg["project"]["dir"]))

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)
    print("\tCreated: %s." % file_)


def generate_tools_sample_coverage(file_):
    """
    This function creates the "coverage file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    sample_coverage = "\n".join(
        [
            "#!/usr/bin/env bash",
            "#-------------------------------------------------------------------------------------",
            "# NAME:",
            "#    tools/sample-coverage.sh",
            "#",
            "# DESCRIPTION:",
            "#    Run pytest coverage report and emit HTML.",
            "#",
            "",
            "set -x",
            "",
            "pylint --rcfile .pylintrc {project_dir}/scripts",
            "",
            "pytest --cov={project_dir}/scripts --cov-report html:cov_html {project_dir}/tests",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sample_coverage.format(project_dir=cfg["project"]["dir"]))

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)
    print("\tCreated: %s." % file_)


def generate_tools_sample_deploy(file_):
    """
    This function creates the "deploy file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    sample_deploy = "\n".join(
        [
            "#!/usr/bin/env bash",
            "#-------------------------------------------------------------------------------------",
            "# NAME:",
            "#    tools/sample-deploy.sh",
            "#",
            "# USAGE:",
            "#    sh tools/sample-deploy.sh $(ROLE) $(ROLE2) $(ROLE3) ...",
            "#",
            "",
            "for role in $*",
            "do",
            '    echo "Uploading RPM to server_role-$role yum repo..."',
            "    scp *.rpm test.example.com:/apps/docs/yum/SILO/production/$role/RPMS/",
            '    ssh -t ${USER}@test.example.com "cd /apps/docs/yum/SILO/production/$role/RPMS/; sudo chmod -R 775 .; sudo chown -R test:test .; sudo -u test createrepo -c cache ."',
            "done",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sample_deploy)

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)
    print("\tCreated: %s." % file_)


def generate_tools_sample_sign(file_):
    """
    This function creates the "sign file" if it does not exist in new build system.
    :param file_:
    :return:
    """
    if Path(file_).is_file():
        os.chmod(file_, 0o775)
        print("\tFile: {} already exists.".format(file_))
        return

    sample_sign = "\n".join(
        [
            "#!/usr/bin/env bash",
            "#-------------------------------------------------------------------------------------",
            "# NAME:",
            "#    tools/sample-sign.sh",
            "#",
            "# USAGE:",
            "#    sh tools/sample-sign.sh $(RPMDIR)/$(RPMNAME)-$(VERSION)-$(RELEASE).$(ARCH).rpm",
            "#",
            "",
            "RPM=$1",
            "rpm-sign.exp $RPM",
            "\n",
        ]
    )

    with open(file_, "w") as f:
        f.write(sample_sign)

    # this file has given the permissions to read write and executable
    os.chmod(file_, 0o775)
    print("\tCreated: %s." % file_)


def interrogate_build_system():
    """
    This function Validates the auto-generated CoDE configuration files.
    :return:
    """
    print(
        "\n--[Verification]----------------------------------------------------------"
    )
    verify_jenkinsfile("Jenkinsfile")
    verify_setup_py("setup.py")
    verify_makefile("Makefile")
    verify_sonarqube("sonar-project.properties")


def verify_jenkinsfile(file_):
    """
    verify "Jenkinsfile" file contents and highlight files and folders that are specified in file
    which are not found in project directory.
    :param file_:
    :return:
    """
    if not Path(file_).is_file():
        return

    print(
        "\n--[%s]------------------------------------------------------------" % file_
    )
    with open(file_) as f:
        sub_regex = re.compile("\s+|-\s*|^.+:\s*|{.+")
        sh_regex = re.compile(r'\w\w"(\w*/\w*.sh)"')

        for line in f:
            line = sub_regex.sub("", line.strip())
            # check all the sh files mentioned in Jenkinsfile exists in the path
            match = sh_regex.search(line)
            if match:
                if Path(match.group(1)).is_file():
                    print("\tVERIFIED: {} exists.".format(match.group(1)))
                else:
                    print("\tBROKEN: {} does NOT exist.".format(match.group(1)))


def verify_setup_py(file_):
    """
    Extract version & author email information.

    :param file_:
    :return:
    """
    if not Path(file_).is_file():
        return

    print("--[%s]-------------------------------------------------------------" % file_)

    with open(file_) as f:
        for line in f:
            version = re.search("version=[\"'](.+)['\"],", line)
            if version:
                print("\tsetup.py: version: %s" % version.group(1))

            email = re.search("author_email=[\"'](.+)['\"],", line)
            if email:
                if email.group(1).strip() == "test@example.com":
                    print("\tsetup.py: author_email = %s (correct)" % email.group(1))
                else:
                    print(
                        "setup.py: author_email = %s (NOT test@example.com)"
                        % email.group()
                    )


def verify_makefile(file_):
    """
    Show Version, DELIVERABLENAME, RPMNAME & project details from Makefile
    :param file_:
    :return:
    """
    if not Path(file_).is_file():
        return

    print("--[%s]----------------------------------------------------------" % file_)
    print(
        "\tMakefile: %s" % cfg["project"].get("VERSION", "")
        + "."
        + cfg["project"].get("RELEASE", "")
    )
    print("\tDELIVERABLENAME: %s" % cfg["project"].get("DELIVERABLENAME", ""))
    print("\tRPMNAME: %s" % cfg["project"].get("RPMNAME", ""))
    print("\tProject: %s" % cfg["project"].get("name", ""))


def verify_sonarqube(file_):
    """
    Validate sonar-project.properties and highlight mismatch in projectName & projectVersion.
    :param file_:
    :return:
    """
    if not Path(file_).is_file():
        return

    print("--[%s]------------------------------------------------------------" % file_)
    with open(file_) as f:
        for line in f:
            if re.search("sonar.projectName=(.+)", line):
                sonar = re.search("sonar.projectName=(.+)", line)

                if sonar.group(1).strip() != cfg["project"]["name"]:
                    print(
                        "\tWARNING: projectName does not match: %s"
                        % cfg["project"]["name"]
                    )
            elif re.search("sonar.projectVersion=(.+)$", line):
                project_version = re.search("sonar.projectVersion=(.+)$", line)
                makefile = (
                    cfg["project"].get("VERSION", "")
                    + "."
                    + cfg["project"].get("RELEASE", "")
                )

                if project_version.group(1).strip() != makefile:
                    print("\tWARNING: projectVersion does not match: %s" % makefile)
                else:
                    print("\tVERIFIED: {}".format(file_))


# Start Execution..
if __name__ == "__main__":
    # read the input command line arguments for generating CoDE configuration.
    parser = argparse.ArgumentParser(
        description="""This python script will attempt to analize your environment and determine
                       if you have a viable CoDE configuration.""",
        usage="cd $PROJECT \n"
        "python SOURCES/apps/bin/curly_code_migration.py --name server_role-SDW --dir SOURCES",
    )

    parser.add_argument("--name", type=str, default="", help="server_role-SDW")
    parser.add_argument("--dir", type=str, default="", help="SOURCES")

    interrogate(parser.parse_args())
    check_for_module_build()
    check_for_makefile()
    check_for_new_build_system()
    print("")
    _ = os.system("git status")

