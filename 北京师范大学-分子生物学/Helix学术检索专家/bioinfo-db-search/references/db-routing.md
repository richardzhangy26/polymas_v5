# 数据库路由与检索规划

本目录完整保留用户原稿列出的 47 个数据库、学术检索与学习资源入口，并补充原工作流实际使用的 NCBI Gene，共 48 个入口。完整目录用于路由选择，不表示每个入口都已接入 API、当前可访问或应在一次任务中全部检索。

数据库首页用于发现；引用证据应尽量指向具体记录或文章。运行时检查真实返回 URL、重定向、访问限制和记录可见性。数据库需要登录、订阅或人工操作时如实说明，不把入口可达当作记录已核验。

## 快速路由

| 用户目标 | 首选入口 | 按需补充 |
|---|---|---|
| 核酸序列与参考记录 | NCBI Gene、NCBI RefSeq、NCBI GenBank | ENA、DDBJ、Ensembl、GENCODE |
| 原始测序与基因组数据 | NCBI SRA、GSA、GWH | ENA、IMG、TCGA GDC |
| 序列相似性检索 | NCBI BLAST | 先确认序列类型、物种范围和数据库；本技能仅提供入口与方案 |
| 基因组定位与注释 | Ensembl、UCSC Genome Browser、GENCODE | TAIR、NCBI Gene、GWH |
| 基因与蛋白表达 | NCBI GEO、GTEx、HPA | GEPIA2、ArrayExpress、TCGA GDC |
| 蛋白功能与结构域 | UniProt、InterPro、Pfam | HPA、STRING |
| 实验或预测结构 | RCSB PDB；AlphaFold DB | SWISS-MODEL；实验和预测必须分栏 |
| 功能、通路与互作 | Gene Ontology、Reactome、KEGG | STRING、UniProt |
| 遗传变异与疾病 | ClinVar、dbSNP | GeneCards、DisGeNET；聚合关联与临床解释分开 |
| 药物、化合物与酶 | ChEMBL、PubChem、BRENDA | DrugBank；检查登录与许可限制 |
| 非编码 RNA | miRBase、RNAcentral | GENCODE |
| 微生物与病毒 | IMG、ViralZone | GenBank、RefSeq、NCBI Taxonomy |
| 物种分类与国内综合入口 | NCBI Taxonomy、NGDC | GSA、GWH |
| 生物医学文献 | PubMed | Science、Web of Science、论文出版社原始页面 |
| 学习资源 | Bilibili、网易公开课 | 仅在用户明确需要教程时单列，不计作学术原始证据 |

初轮通常选择最相关的 1—3 个入口；只有问题跨维度或首选结果不足时扩展。用户指定数据库时优先遵守指定来源，同时保留证据核验要求。

## 完整入口目录

### 1. 核酸与测序数据库

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| NCBI GenBank | https://www.ncbi.nlm.nih.gov/genbank/ | 核酸序列；核对 Accession、版本、物种和记录状态 |
| NCBI BLAST | https://blast.ncbi.nlm.nih.gov/Blast.cgi | 序列相似性搜索入口；需要实际提交序列时说明本轮是否执行 |
| NCBI RefSeq | https://www.ncbi.nlm.nih.gov/refseq/ | 参考基因、转录本和蛋白序列；核对版本与转录本 |
| GSA（国家生物信息中心） | https://ngdc.cncb.ac.cn/gsa/ | 国内原始测序数据；核对项目、样本和访问权限 |
| NCBI SRA | https://www.ncbi.nlm.nih.gov/sra/ | 原始高通量测序数据；核对 BioProject、BioSample、Run 及实验设计 |
| ENA (EMBL-EBI) | https://www.ebi.ac.uk/ena/ | 欧洲核酸档案；核对 INSDC 记录映射、版本和样本 |
| DDBJ | https://www.ddbj.nig.ac.jp/ | 日本核酸数据库；核对 INSDC 记录与版本 |
| GWH 基因组仓库 | https://ngdc.cncb.ac.cn/gwh/ | 国内物种基因组与组装；核对组装版本和注释来源 |

### 2. 基因组浏览器与注释

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| NCBI Gene | https://www.ncbi.nlm.nih.gov/gene/ | 补充入口：基因身份、标准符号、物种和关联记录 |
| Ensembl | https://www.ensembl.org/ | 基因结构、同源关系与序列；核对物种、release 和 transcript |
| UCSC Genome Browser | https://genome.ucsc.edu/ | 基因组轨道、保守性和定位；核对 genome assembly 与 track |
| GENCODE | https://www.gencodegenes.org/ | 人和小鼠高质量基因注释；核对 release、转录本及 lncRNA 类型 |
| TAIR | https://www.arabidopsis.org/ | 拟南芥基因组与功能注释；核对 locus ID 与材料物种 |

### 3. 基因与蛋白表达数据库

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| NCBI GEO | https://www.ncbi.nlm.nih.gov/geo/ | 芯片与 RNA-seq 数据集；核对 GSE/GSM、样本、处理和对照 |
| GEPIA2 | http://gepia2.cancer-pku.cn/ | 肿瘤与正常组织表达在线分析；标明其数据来源和分析条件 |
| GTEx | https://gtexportal.org/ | 人体正常组织表达；核对版本、组织和样本范围 |
| ArrayExpress | https://www.ebi.ac.uk/arrayexpress/ | EBI 表达研究入口；运行时核对实际服务页面、迁移状态和 accession |
| TCGA GDC | https://portal.gdc.cancer.gov/ | 癌症多组学与临床关联数据；区分公开元数据和受控数据 |
| HPA 人类蛋白图谱 | https://www.proteinatlas.org/ | 人体组织、单细胞与蛋白表达；核对证据类型和抗体信息 |

### 4. 蛋白质与结构数据库

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| UniProt | https://www.uniprot.org/ | 蛋白序列与功能；核对 Accession、物种、isoform 和审校状态 |
| RCSB PDB | https://www.rcsb.org/ | 实验解析结构；核对方法、链、残基覆盖、构建体与适用时的分辨率 |
| AlphaFold DB | https://alphafold.ebi.ac.uk/ | 预测结构；明示预测和置信信息，不计入实验结构数量 |
| SWISS-MODEL | https://swissmodel.expasy.org/ | 同源建模；标明模板、覆盖范围与模型质量，不冒充实验结构 |
| Pfam | https://pfam.xfam.org/ | 蛋白家族与结构域模型；核对家族 ID、版本和匹配区间 |
| InterPro | https://www.ebi.ac.uk/interpro/ | 蛋白家族、结构域与功能位点整合注释；核对成员数据库证据 |

### 5. 功能、通路与互作数据库

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| KEGG | https://www.genome.jp/kegg/ | 代谢与信号通路；核对物种、通路 ID、版本与使用限制 |
| Gene Ontology (GO) | https://geneontology.org/ | BP、CC、MF 功能注释；核对 GO ID、证据代码和物种 |
| Reactome | https://reactome.org/ | 人类及映射物种通路；核对 stable ID、物种和注释依据 |
| STRING | https://string-db.org/ | 蛋白关联网络；区分实验、数据库、文本挖掘等证据通道 |

### 6. 遗传变异与疾病关联数据库

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| dbSNP | https://www.ncbi.nlm.nih.gov/snp/ | 变异标识与位置；核对 rsID、参考组装和等位基因 |
| ClinVar | https://www.ncbi.nlm.nih.gov/clinvar/ | 变异与临床表型解释；核对 accession、review status、日期和冲突解释 |
| GeneCards | https://www.genecards.org/ | 人类基因聚合信息；作为发现入口，关键结论回查原始来源 |
| DisGeNET | https://www.disgenet.org/ | 基因与疾病关联聚合；区分证据来源、评分和直接实验支持 |

疾病相关查询仅作学术证据介绍，不据数据库条目对个人作诊断或用药决定。

### 7. 药物、化合物与酶学数据库

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| DrugBank | https://go.drugbank.com/ | 药物与靶点；核对登录、许可限制和原始靶点证据 |
| ChEMBL | https://www.ebi.ac.uk/chembl/ | 小分子生物活性；核对 assay、单位、靶点和文献来源 |
| BRENDA | https://www.brenda-enzymes.org/ | 酶、底物与动力学；核对物种、实验条件、单位和引用 |
| PubChem | https://pubchem.ncbi.nlm.nih.gov/ | 化合物结构、性质与 BioAssay；核对 CID/AID 和数据来源 |

### 8. 非编码 RNA 数据库

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| miRBase | https://www.mirbase.org/ | miRNA 命名与序列；核对物种、前体/成熟体 ID 和版本 |
| RNAcentral | https://rnacentral.org/ | 多类非编码 RNA 整合记录；核对 URS、物种和成员数据库 |

### 9. 微生物与病毒资源

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| IMG | https://img.jgi.doe.gov/ | 微生物基因组与宏基因组；核对样本、组装和项目权限 |
| ViralZone | https://viralzone.expasy.org/ | 病毒分类、基因组和蛋白知识；关键事实回查引用与序列记录 |

### 10. 分类与综合平台

| 数据库 | 入口 | 适用范围与核验重点 |
|---|---|---|
| NCBI Taxonomy | https://www.ncbi.nlm.nih.gov/Taxonomy/ | 物种分类与 Taxonomy ID；注意名称更新和同物异名 |
| NGDC 国家生物信息中心 | https://ngdc.cncb.ac.cn/ | 国内生物信息资源总入口；按目标路由到具体子库并引用记录页 |

### 11. 文献检索与学习资源

| 数据库／资源 | 入口 | 适用范围与核验重点 |
|---|---|---|
| PubMed (NCBI) | https://pubmed.ncbi.nlm.nih.gov/ | 生物医学文献；核对 PMID、文章类型、日期和实际可见范围 |
| Science | https://www.science.org/ | 期刊内容入口；按文章页核对 DOI、文章类型和访问范围 |
| Web of Science | https://webofscience.clarivate.cn/ | 引文检索；可能需要机构订阅，引用结论应回到原论文 |
| Bilibili | https://www.bilibili.com | 教程视频；仅作学习资源，注明作者、日期和非原始证据属性 |
| 网易公开课 | https://www.icourse163.org | 课程学习入口；仅作学习资源，不替代数据库或论文证据 |

课程知识库用于解释课程语境，不能替代原始数据库记录。教程、课程视频、聚合页和搜索片段均不能计入原始研究数量。

## 规划规则

1. 将目标拆成“实体／物种＋要查的关系或数据＋必要限制”。初轮选最相关的 1—3 个来源，按问题需要跨库，而非逐库扫完。
2. 原始名称原样保留；仅使用已确认同义词作并列查询，不擅自增加疾病、年份、组织或实验方法。可能改变对象的缩写先确认。
3. 普通文献检索不默认限近五年。用户给相对日期时，以执行日转换为明确区间，记录时区和日期字段；对未来日期或日期未知结果单列核验。
4. 构造网页检索式可使用主题词与 `site:` 域名，但检索服务未提供强制域名约束时，必须回查实际返回 URL。数据库高级查询语法只在相应界面支持且已核实时使用。
5. PubMed 布尔逻辑用括号明确分组。字段标签、日期范围和文献类型依据 PubMed 实际帮助页面；未知字段不编造，通用检索后端也不能假定会原样执行数据库语法。
6. 检索式和手动入口可输出为方案，但只有工具实际执行过的查询才写入“实际检索条件”。
7. 同一记录跨 INSDC、聚合平台或镜像重复出现时，以稳定标识与版本去重，同时保留实际访问来源。

## 特殊任务

- 序列：Accession、版本及所需转录本明确后才选序列。核酸摘要最多展示前 200 nt；蛋白摘要最多 200 aa，注明截断及原始记录链接。未读取实际序列时仅返回标识和获取指引。
- BLAST：只有实际提交序列并获得任务结果时才报告比对命中；否则提供参数方案和操作入口，标注“尚未执行”。
- 结构：同一蛋白的片段、突变体、复合物或异源表达构建体分别标注；片段实验结构不能表述为全长实验结构。
- 表达与组学：仅提取可读元数据；没有读取样本表时把样本量记为未核验。公开元数据与受控下载权限分别表述。
- 变异：同时记录参考组装、等位基因、解释状态、review status 和更新时间；存在冲突提交时并列呈现。
- 药物与活性：保留实验体系、靶点、数值、单位和来源；数据库关联不自动等于临床有效性。
- 文献数量不足：先在原条件内核查同义词和其他合适来源；仍不足则如实返回，不以综述、教程或跨物种论文凑齐。
