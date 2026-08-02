# Changelog

## 0.1.0 (2026-08-02)


### Features

* **release:** carry the prerelease sync in this repo ([c3b54ad](https://github.com/ethrive-io/whitepaper/commit/c3b54ad21fcf164ebb674555408b67a5e80f6ae3))


### Bug Fixes

* **commit-lint:** accept uppercase scopes and the adr type ([299d736](https://github.com/ethrive-io/whitepaper/commit/299d736cde1bf5d56dc18840315bfae83e7a1dc0))
* **commit-lint:** exempt history that predates the gate, or it can never go green ([f62c8f5](https://github.com/ethrive-io/whitepaper/commit/f62c8f578f4f0f24a8b18147bb33d005fc3add5d))
* **commit-lint:** repair the workflow YAML I broke inserting a comment ([89f4074](https://github.com/ethrive-io/whitepaper/commit/89f40749798db67bf5f8576ea1e65122ff2851b1))
* **gates:** the last bare gate_check, in the script written after the sweep ([fed01d9](https://github.com/ethrive-io/whitepaper/commit/fed01d95ca7e4de45b5123e33b4b976b6831cd77))
* **release:** name the release PR "Release vX.Y.Z" and drop the beep-boop header ([8586e43](https://github.com/ethrive-io/whitepaper/commit/8586e4369956d57a31d4657bd06e7c8267c63117))
* **release:** set the GROUP title pattern, the one release-please actually reads ([b007a2e](https://github.com/ethrive-io/whitepaper/commit/b007a2e2665ea4789a6d6e953cc2ee409ddd190c))


### Performance

* **release:** pin bootstrap-sha so release-please stops walking 500 commits ([c5cd497](https://github.com/ethrive-io/whitepaper/commit/c5cd49763d6f136d683adbd0ea506bd04f0b339b))


### Documentation

* follow the specs lower-kebab-case document rename ([883aa71](https://github.com/ethrive-io/whitepaper/commit/883aa71bc9a9a691788b479549df9b10fb2400e9))
* point the licence link at LICENSE.md, the file that exists ([75bac83](https://github.com/ethrive-io/whitepaper/commit/75bac83ed2db1cd1ba26f236e76e01ff42fc8db1))


### CI

* **commit-lint:** drop the pull_request trigger the file itself argued against ([d69abee](https://github.com/ethrive-io/whitepaper/commit/d69abee071091f4c43635add50abbc2ef5b6bfbd))
* **commit-lint:** gate commit subjects, because release-please drops what it cannot parse ([b4ae84d](https://github.com/ethrive-io/whitepaper/commit/b4ae84d645d945560a773c3e5a26138cadaf3ec3))
* **release:** allow release-please to be triggered manually ([c468204](https://github.com/ethrive-io/whitepaper/commit/c46820434e204fa77ed67b614ff651e20648f8cd))
* **release:** run release-please on the next preview branch ([0e8361e](https://github.com/ethrive-io/whitepaper/commit/0e8361e0e91db4f259a62fc7293672f8e00c0e38))
