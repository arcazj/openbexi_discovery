# Commercial Use and Licensing

Checked against official sources on October 4, 2026. The first version's installed Python dependencies, versions, and preserved notices are recorded in [third-party notices](THIRD_PARTY_NOTICES.md). Recheck the inventory when dependencies or data sources change.

## Project license

Original project code and documentation use the [OpenBEXI Discovery Proprietary Commercial and Evaluation License](LICENSE). Personal, noncommercial learning, research, and evaluation are permitted within its terms. **Commercial use and redistribution require separate written permission from the applicable rights holder.** This is source-available proprietary software, not an open-source license. Contact the [project maintainer](https://github.com/arcazj/openbexi_discovery) for commercial terms; no pricing, paid support, or additional warranty is implied by downloading the software.

Users must independently verify every result before relying on or sharing it and are responsible for their decisions. The tool is for learning and research, not professional advice. The [disclaimer](DISCLAIMER.md) contains accuracy limitations, warranty exclusions, and liability exclusions to the extent permitted by applicable law. Mandatory legal rights and liabilities are preserved. Have jurisdiction-specific commercial agreements reviewed by a qualified licensing professional.

## Software dependencies

| Component | License | Commercial-use conditions |
|---|---|---|
| [Three.js](https://github.com/mrdoob/three.js/blob/dev/LICENSE) | MIT | Commercial use and distribution permitted. Retain copyright and permission notices in copies or substantial portions. |
| [FastAPI](https://github.com/fastapi/fastapi/blob/master/LICENSE) | MIT | Commercial use and distribution permitted, with the same notice requirements. |
| [OpenAI Python SDK](https://github.com/openai/openai-python/blob/main/LICENSE) | Apache-2.0 | Commercial use permitted. Redistribution requires the license, applicable retained notices, notices of modified files, and applicable `NOTICE` attributions if supplied. |

Three.js is deferred and is not bundled in this release. The full Python runtime inventory and license texts are linked from `THIRD_PARTY_NOTICES.md`; retain applicable notices when distributing dependencies. Transitive dependencies include MPL-2.0 code: follow its source-availability and notice requirements when redistributing those libraries or modifications, as explained in [Mozilla's MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/). Review any additional fonts, icons, assets, and sample data before distribution.

## Hosted AI services

OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, and custom providers have separate service terms, usage policies, account permissions, and billing. A project license does not grant API credits or rights to provider services. The SDK license covers client software. Hosted API access is governed separately by the applicable [OpenAI Services Agreement](https://openai.com/policies/services-agreement/), [Service Terms](https://openai.com/policies/service-terms/), and [Usage Policies](https://openai.com/policies/usage-policies/). The Services Agreement permits API integration into customer applications offered to end users; applicable usage charges still apply.

## Implemented data sources

| Source | Reuse terms and conditions |
|---|---|
| [Ensembl](https://www.ensembl.org/info/about/legal/disclaimer.html) | Ensembl-generated data is unrestricted. Third-party data can have separate constraints; check the underlying source and retain attribution. |
| [GWAS Catalog](https://www.ebi.ac.uk/gwas/docs/about/) | Curated catalog data follows [EMBL-EBI Terms of Use](https://www.ebi.ac.uk/about/terms-of-use/), including original data-owner rights and attribution expectations. Summary statistics generally use CC0; verify each study's terms. Do not apply CC0 to all catalog content. |
| [PubMed / NLM](https://www.nlm.nih.gov/databases/download.html) | Publicly accessible downloads do not require a signed license. Acknowledge NLM, avoid implying endorsement, and maintain current redistributed records or disclose staleness. Abstracts can be copyrighted; access does not grant blanket commercial reuse rights. |

Full-text publication rights are separate. If adding [PMC Open Access content](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/), check each article's license: some terms restrict commercial reuse, and retrieval must use permitted services.

## Future integrations

- **UCSC:** Commercial use of the public website/API does not require a license. Check individual track and assembly restrictions. Certain locally installed Genome Browser, BLAT, and LiftOver software, and liftOver chain files, have separate commercial licensing requirements. See [UCSC licensing](https://genome.ucsc.edu/license/).
- **ClinVar:** NCBI places no additional restrictions on molecular-data use or distribution but cannot clear third-party intellectual-property claims. Retain attribution. See [NCBI policies](https://www.ncbi.nlm.nih.gov/home/about/policies/) and [ClinVar data-use guidance](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/).

## Application requirements

Expose these notes through **Help → Licences** and source details. Make the [NCBI copyright and disclaimer notice](https://www.ncbi.nlm.nih.gov/home/about/policies/) evident in source details and Help for PubMed and other NCBI integrations. Retain attribution and applicable terms in exports. Verify permissions for caching, AI processing, display, and redistribution for the content actually used. Recheck terms for the final dependency versions and datasets before commercial distribution.


See the [Discovery licensing roadmap](documentation/LICENSING_ROADMAP.md) for future offering ideas. The current LICENSE governs this release; roadmap proposals grant no additional rights.
