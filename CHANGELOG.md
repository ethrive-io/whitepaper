# Changelog

## 0.1.0 (2026-07-31)


### Bug Fixes

* **commit-lint:** accept uppercase scopes and the adr type ([299d736](https://github.com/ethrive-io/whitepaper/commit/299d736cde1bf5d56dc18840315bfae83e7a1dc0))
* **commit-lint:** exempt history that predates the gate, or it can never go green ([f62c8f5](https://github.com/ethrive-io/whitepaper/commit/f62c8f578f4f0f24a8b18147bb33d005fc3add5d))
* **commit-lint:** repair the workflow YAML I broke inserting a comment ([89f4074](https://github.com/ethrive-io/whitepaper/commit/89f40749798db67bf5f8576ea1e65122ff2851b1))
* **release:** name the release PR "Release vX.Y.Z" and drop the beep-boop header ([8586e43](https://github.com/ethrive-io/whitepaper/commit/8586e4369956d57a31d4657bd06e7c8267c63117))


### Performance

* **release:** pin bootstrap-sha so release-please stops walking 500 commits ([c5cd497](https://github.com/ethrive-io/whitepaper/commit/c5cd49763d6f136d683adbd0ea506bd04f0b339b))


### CI

* **commit-lint:** gate commit subjects, because release-please drops what it cannot parse ([b4ae84d](https://github.com/ethrive-io/whitepaper/commit/b4ae84d645d945560a773c3e5a26138cadaf3ec3))
* **release:** allow release-please to be triggered manually ([c468204](https://github.com/ethrive-io/whitepaper/commit/c46820434e204fa77ed67b614ff651e20648f8cd))
