# Tableau migration report: HR Dashboard

## Tables and extracted rows

| Table | Hyper table | Rows | Columns |
|---|---|---:|---:|
| HumanResources | `Extract` | 8950 | 14 |

## Relationships


## Calculations

| Caption | Class | Status | DAX / reason |
|---|---|---|---|
| % Total Terminated | table_calc | supported (semantics approximated) | `DIVIDE([Total Terminated], CALCULATE([Total Terminated], ALLSELECTED()))` |
| % Total Hired | table_calc | supported (semantics approximated) | `DIVIDE([Total Hired], CALCULATE([Total Hired], ALLSELECTED()))` |
| Rank Top 2 | table_calc | table_calc | `` |
| Status | row | supported | `IF(ISBLANK('HumanResources'[Termdate]), "Hired", "Terminated")` |
| Highlight Max | table_calc | table_calc | `` |
| Total Hired | aggregate | supported | `COUNT('HumanResources'[Employee_ID])` |
| Total Terminated | aggregate | supported | `COUNTX('HumanResources', IF(NOT(ISBLANK('HumanResources'[Termdate])), 'HumanResources'[Employee_ID]))` |
| Total Active | aggregate | supported | `COUNTX('HumanResources', IF(ISBLANK('HumanResources'[Termdate]), 'HumanResources'[Employee_ID]))` |
| Location | row | supported | `SWITCH('HumanResources'[State], "New York", "HQ", "Branch")` |
| Age | row | supported | `DATEDIFF('HumanResources'[Birthdate], TODAY(), YEAR)` |
| Age Groups | row | supported | `IF(('HumanResources'[Age] < 25), ">25", IF((('HumanResources'[Age] >= 25) && ('HumanResources'[Age] < 35)), "25-34", IF((('HumanResources'[Age] >= 35) && ('HumanResources'[Age] < 45)), "35-44", IF((('HumanResources'[Age] >= 45) && ('HumanResources'[Age] < 55)), "45-54", IF(('HumanResources'[Age] >= 55), "55+", BLANK())))))` |
| Full Name | row | supported | `(('HumanResources'[First Name] & " ") & 'HumanResources'[Last Name])` |
| Length of Hire | row | supported | `IF(ISBLANK('HumanResources'[Termdate]), DATEDIFF('HumanResources'[Hiredate], TODAY(), YEAR), DATEDIFF('HumanResources'[Hiredate], 'HumanResources'[Termdate], YEAR))` |
| % Highlight Max | table_calc | table_calc | `` |
| Rank Top 1 | table_calc | table_calc | `` |

## Auto measures

- **AVG Salary**: `AVERAGE('HumanResources'[Salary])`
- **AVG Age**: `AVERAGE('HumanResources'[Age])`
- **SUM Length of Hire**: `SUM('HumanResources'[Length of Hire])`
- **SUM Age**: `SUM('HumanResources'[Age])`
- **SUM Salary**: `SUM('HumanResources'[Salary])`

## Lead overrides

- None.

## Visuals

| Dashboard | ID | Type | Position | Fields |
|---|---|---|---|---|
| HR | Summary | `z_0_228` | image | `{"x":0.0,"y":0.0,"w":1400.0,"h":800.0,"z":0}` | `[]` |
| HR | Summary | `z_1_133` | image | `{"x":20.01,"y":20.0,"w":69.99,"h":55.0,"z":100}` | `[]` |
| HR | Summary | `z_3_135` | image | `{"x":30.0,"y":158.33,"w":49.99,"h":38.0,"z":6500}` | `[]` |
| HR | Summary | `z_5_136` | image | `{"x":30.0,"y":206.33,"w":49.99,"h":38.0,"z":6600}` | `[]` |
| HR | Summary | `z_7_151` | textbox | `{"x":30.0,"y":317.66,"w":49.99,"h":20.0,"z":400}` | `[]` |
| HR | Summary | `z_8_152` | shape | `{"x":30.0,"y":337.66,"w":49.99,"h":11.0,"z":500}` | `[]` |
| HR | Summary | `z_9_141_shown` | image | `{"x":30.0,"y":348.66,"w":49.99,"h":30.0,"z":6700}` | `[]` |
| HR | Summary | `z_9_141_hidden` | image | `{"x":30.0,"y":348.66,"w":49.99,"h":30.0,"z":6800}` | `[]` |
| HR | Summary | `z_11_153` | textbox | `{"x":30.0,"y":451.98,"w":49.99,"h":20.0,"z":800}` | `[]` |
| HR | Summary | `z_12_154` | shape | `{"x":30.0,"y":471.98,"w":49.99,"h":11.0,"z":900}` | `[]` |
| HR | Summary | `z_13_142` | image | `{"x":30.0,"y":482.98,"w":49.99,"h":38.0,"z":1000}` | `[]` |
| HR | Summary | `z_15_143` | image | `{"x":30.0,"y":530.98,"w":49.99,"h":38.0,"z":1100}` | `[]` |
| HR | Summary | `z_17_155` | textbox | `{"x":30.0,"y":628.98,"w":49.99,"h":20.0,"z":1200}` | `[]` |
| HR | Summary | `z_18_156` | shape | `{"x":30.0,"y":648.98,"w":49.99,"h":11.0,"z":1300}` | `[]` |
| HR | Summary | `z_19_144` | image | `{"x":30.0,"y":659.98,"w":49.99,"h":25.0,"z":1400}` | `[]` |
| HR | Summary | `z_21_145` | image | `{"x":30.0,"y":694.98,"w":49.99,"h":30.0,"z":1500}` | `[]` |
| HR | Summary | `z_23_146` | image | `{"x":30.0,"y":734.98,"w":49.99,"h":30.02,"z":1600}` | `[]` |
| HR | Summary | `z_24_13` | textbox | `{"x":110.0,"y":0.0,"w":675.0,"h":70.0,"z":1700}` | `[]` |
| HR | Summary | `z_26_19` | textbox | `{"x":117.0,"y":77.0,"w":381.99,"h":31.0,"z":1800}` | `[]` |
| HR | Summary | `z_27_42` | textbox | `{"x":117.0,"y":108.0,"w":381.99,"h":28.0,"z":1900}` | `[]` |
| HR | Summary | `z_28_43` | native | `{"x":117.0,"y":136.0,"w":381.99,"h":43.0,"z":6900}` | `[{"role": "Values", "field": "HumanResources.Total Active"}]` |
| HR | Summary | `z_29_44` | shape | `{"x":117.0,"y":179.0,"w":381.99,"h":1.0,"z":2100}` | `[]` |
| HR | Summary | `z_30_49` | textbox | `{"x":117.0,"y":185.0,"w":187.0,"h":22.0,"z":2200}` | `[]` |
| HR | Summary | `z_31_50` | native | `{"x":117.0,"y":207.0,"w":187.0,"h":49.0,"z":7000}` | `[{"role": "Values", "field": "HumanResources.Total Hired"}]` |
| HR | Summary | `z_32_51` | native | `{"x":117.0,"y":256.0,"w":187.0,"h":70.0,"z":7100}` | `[{"role": "Category", "field": "HumanResources.Hiredate (Year)"}, {"role": "Y", "field": "HumanResources.Total Hired"}]` |
| HR | Summary | `z_33_47` | shape | `{"x":304.0,"y":185.0,"w":1,"h":141.0,"z":2500}` | `[]` |
| HR | Summary | `z_34_53` | textbox | `{"x":304.99,"y":185.0,"w":193.9,"h":22.0,"z":2600}` | `[]` |
| HR | Summary | `z_35_54` | native | `{"x":304.99,"y":207.0,"w":193.9,"h":49.0,"z":7200}` | `[{"role": "Values", "field": "HumanResources.Total Terminated"}]` |
| HR | Summary | `z_36_55` | native | `{"x":304.99,"y":256.0,"w":193.9,"h":70.0,"z":7300}` | `[{"role": "Category", "field": "HumanResources.Termdate (Year)"}, {"role": "Y", "field": "HumanResources.Total Terminated"}]` |
| HR | Summary | `z_37_58` | shape | `{"x":126.99,"y":336.0,"w":123.33,"h":30.0,"z":2900}` | `[]` |
| HR | Summary | `z_38_57` | textbox | `{"x":250.32,"y":336.0,"w":115.32,"h":30.0,"z":3000}` | `[]` |
| HR | Summary | `z_39_59` | shape | `{"x":365.64,"y":336.0,"w":123.33,"h":30.0,"z":3100}` | `[]` |
| HR | Summary | `z_40_60` | native | `{"x":117.0,"y":366.0,"w":381.99,"h":173.99,"z":7400}` | `[{"role": "Category", "field": "HumanResources.Department"}, {"role": "Y", "field": "HumanResources.Total Hired"}, {"role": "Series", "field": "HumanResources.Status"}]` |
| HR | Summary | `z_41_63` | shape | `{"x":126.99,"y":544.99,"w":124.66,"h":30.0,"z":3300}` | `[]` |
| HR | Summary | `z_42_62` | textbox | `{"x":251.65,"y":544.99,"w":112.66,"h":30.0,"z":3400}` | `[]` |
| HR | Summary | `z_43_64` | shape | `{"x":364.31,"y":544.99,"w":124.66,"h":30.0,"z":3500}` | `[]` |
| HR | Summary | `z_44_67` | native | `{"x":117.0,"y":574.99,"w":287.0,"h":200.01,"z":7500}` | `[{"role": "Category", "field": "HumanResources.State"}, {"role": "Y", "field": "HumanResources.Total Hired"}]` |
| HR | Summary | `z_45_66` | native | `{"x":404.0,"y":574.99,"w":94.98,"h":200.01,"z":7600}` | `[{"role": "Category", "field": "HumanResources.Location"}, {"role": "Y", "field": "HumanResources.Total Hired"}, {"role": "Series", "field": "HumanResources.Location"}]` |
| HR | Summary | `z_46_25` | textbox | `{"x":532.99,"y":77.0,"w":840.0,"h":31.0,"z":3800}` | `[]` |
| HR | Summary | `z_47_71` | textbox | `{"x":532.99,"y":113.0,"w":152.0,"h":26.0,"z":3900}` | `[]` |
| HR | Summary | `z_48_72` | native | `{"x":532.99,"y":139.0,"w":152.0,"h":268.99,"z":7700}` | `[{"role": "Category", "field": "HumanResources.Status"}, {"role": "Y", "field": "HumanResources.% Total Hired"}]` |
| HR | Summary | `z_49_31` | shape | `{"x":689.99,"y":113.0,"w":1,"h":295.0,"z":4100}` | `[]` |
| HR | Summary | `z_50_74` | textbox | `{"x":695.98,"y":113.0,"w":348.0,"h":26.0,"z":4200}` | `[]` |
| HR | Summary | `z_51_78` | native | `{"x":695.98,"y":139.0,"w":348.0,"h":70.0,"z":7800}` | `[{"role": "Category", "field": "HumanResources.Education Level"}, {"role": "Y", "field": "HumanResources.Total Hired"}]` |
| HR | Summary | `z_52_77` | native | `{"x":695.98,"y":209.0,"w":273.0,"h":199.0,"z":7900}` | `[{"role": "Rows", "field": "HumanResources.Age Groups"}, {"role": "Columns", "field": "HumanResources.Education Level"}, {"role": "Values", "field": "HumanResources.Total Hired"}]` |
| HR | Summary | `z_53_75` | native | `{"x":968.98,"y":209.0,"w":70.99,"h":199.0,"z":8000}` | `[{"role": "Category", "field": "HumanResources.Age Groups"}, {"role": "Y", "field": "HumanResources.Total Hired"}]` |
| HR | Summary | `z_54_79` | shape | `{"x":1048.98,"y":113.0,"w":1,"h":295.0,"z":4600}` | `[]` |
| HR | Summary | `z_55_81` | textbox | `{"x":1054.97,"y":113.0,"w":317.98,"h":26.0,"z":4700}` | `[]` |
| HR | Summary | `z_56_82` | native | `{"x":1054.97,"y":139.0,"w":317.98,"h":268.99,"z":8100}` | `[{"role": "Rows", "field": "HumanResources.Performance Rating"}, {"role": "Columns", "field": "HumanResources.Education Level"}, {"role": "Values", "field": "HumanResources.% Total Hired"}]` |
| HR | Summary | `z_57_28` | textbox | `{"x":532.99,"y":459.0,"w":840.0,"h":31.0,"z":4900}` | `[]` |
| HR | Summary | `z_58_84` | textbox | `{"x":532.99,"y":495.0,"w":416.01,"h":26.0,"z":5000}` | `[]` |
| HR | Summary | `z_59_85` | native | `{"x":532.99,"y":521.0,"w":416.01,"h":253.98,"z":8200}` | `[{"role": "Category", "field": "HumanResources.Education Level"}, {"role": "Y", "field": "HumanResources.AVG Salary"}, {"role": "Series", "field": "HumanResources.Gender"}]` |
| HR | Summary | `z_60_34` | shape | `{"x":954.0,"y":495.0,"w":1,"h":280.0,"z":5200}` | `[]` |
| HR | Summary | `z_61_87` | textbox | `{"x":959.99,"y":495.0,"w":413.0,"h":26.0,"z":5300}` | `[]` |
| HR | Summary | `z_62_88` | native | `{"x":959.99,"y":521.0,"w":413.0,"h":254.0,"z":8300}` | `[{"role": "X", "field": "HumanResources.AVG Age"}, {"role": "Y", "field": "HumanResources.AVG Salary"}, {"role": "Category", "field": "HumanResources.Job Title"}]` |
| HR | Summary | `z_63_121` | textbox | `{"x":433.01,"y":77.0,"w":84.99,"h":32.0,"z":5500}` | `[]` |
| HR | Summary | `z_64_123` | slicer | `{"x":749.99,"y":9.0,"w":142.0,"h":51.0,"z":8400}` | `[{"field": "HumanResources.Gender"}]` |
| HR | Summary | `z_65_124` | slicer | `{"x":892.0,"y":9.0,"w":142.0,"h":51.0,"z":8500}` | `[{"field": "HumanResources.Status"}]` |
| HR | Summary | `z_66_125` | slicer | `{"x":1034.0,"y":9.0,"w":142.0,"h":51.0,"z":8600}` | `[{"field": "HumanResources.Location"}]` |
| HR | Summary | `z_67_126` | slicer | `{"x":1176.0,"y":9.0,"w":142.0,"h":51.0,"z":8700}` | `[{"field": "HumanResources.Hiredate (Year)"}]` |
| HR | Summary | `z_68_127_shown` | image | `{"x":1329.01,"y":25.0,"w":51.0,"h":48.0,"z":8800}` | `[]` |
| HR | Summary | `z_68_127_hidden` | image | `{"x":1329.01,"y":25.0,"w":51.0,"h":48.0,"z":8900}` | `[]` |
| HR | Summary | `z_70_139` | textbox | `{"x":90.01,"y":240.0,"w":1309.0,"h":320.0,"z":6200}` | `[]` |
| HR | Summary | `z_72_161` | textbox | `{"x":1319.0,"y":10.0,"w":70.99,"h":30.0,"z":6300}` | `[]` |
| HR | Summary | `z_73_223` | shape | `{"x":23.0,"y":158.0,"w":6.01,"h":40.0,"z":6400}` | `[]` |
| HR | Details | `z_0_300` | image | `{"x":0.0,"y":0.0,"w":1400.0,"h":800.0,"z":0}` | `[]` |
| HR | Details | `z_1_133` | image | `{"x":20.01,"y":20.0,"w":69.99,"h":55.0,"z":100}` | `[]` |
| HR | Details | `z_3_135` | image | `{"x":30.0,"y":158.33,"w":49.99,"h":38.0,"z":6400}` | `[]` |
| HR | Details | `z_5_136` | image | `{"x":30.0,"y":206.33,"w":49.99,"h":38.0,"z":6500}` | `[]` |
| HR | Details | `z_7_151` | textbox | `{"x":30.0,"y":317.66,"w":49.99,"h":20.0,"z":400}` | `[]` |
| HR | Details | `z_8_152` | shape | `{"x":30.0,"y":337.66,"w":49.99,"h":11.0,"z":500}` | `[]` |
| HR | Details | `z_9_141_shown` | image | `{"x":30.0,"y":348.66,"w":49.99,"h":30.0,"z":6600}` | `[]` |
| HR | Details | `z_9_141_hidden` | image | `{"x":30.0,"y":348.66,"w":49.99,"h":30.0,"z":6700}` | `[]` |
| HR | Details | `z_11_153` | textbox | `{"x":30.0,"y":451.98,"w":49.99,"h":20.0,"z":800}` | `[]` |
| HR | Details | `z_12_154` | shape | `{"x":30.0,"y":471.98,"w":49.99,"h":11.0,"z":900}` | `[]` |
| HR | Details | `z_13_142` | image | `{"x":30.0,"y":482.98,"w":49.99,"h":38.0,"z":1000}` | `[]` |
| HR | Details | `z_15_143` | image | `{"x":30.0,"y":530.98,"w":49.99,"h":38.0,"z":1100}` | `[]` |
| HR | Details | `z_17_155` | textbox | `{"x":30.0,"y":628.98,"w":49.99,"h":20.0,"z":1200}` | `[]` |
| HR | Details | `z_18_156` | shape | `{"x":30.0,"y":648.98,"w":49.99,"h":11.0,"z":1300}` | `[]` |
| HR | Details | `z_19_144` | image | `{"x":30.0,"y":659.98,"w":49.99,"h":25.0,"z":1400}` | `[]` |
| HR | Details | `z_21_145` | image | `{"x":30.0,"y":694.98,"w":49.99,"h":30.0,"z":1500}` | `[]` |
| HR | Details | `z_23_146` | image | `{"x":30.0,"y":734.98,"w":49.99,"h":30.02,"z":1600}` | `[]` |
| HR | Details | `z_24_13` | textbox | `{"x":110.0,"y":0.0,"w":672.99,"h":70.0,"z":1700}` | `[]` |
| HR | Details | `z_26_292` | textbox | `{"x":117.0,"y":77.0,"w":1256.0,"h":37.0,"z":1800}` | `[]` |
| HR | Details | `z_27_226_shown` | image | `{"x":117.0,"y":114.0,"w":24.99,"h":43.0,"z":6800}` | `[]` |
| HR | Details | `z_27_226_hidden` | image | `{"x":117.0,"y":114.0,"w":24.99,"h":43.0,"z":6900}` | `[]` |
| HR | Details | `z_28_222` | textbox | `{"x":141.99,"y":114.0,"w":77.01,"h":43.0,"z":2100}` | `[]` |
| HR | Details | `z_29_227` | slicer | `{"x":117.0,"y":161.0,"w":102.0,"h":53.0,"z":7000}` | `[{"field": "HumanResources.Employee_ID"}]` |
| HR | Details | `z_30_215` | shape | `{"x":219.0,"y":114.0,"w":12.99,"h":43.0,"z":2300}` | `[]` |
| HR | Details | `z_31_240_shown` | image | `{"x":231.99,"y":114.0,"w":24.99,"h":42.0,"z":7100}` | `[]` |
| HR | Details | `z_31_240_hidden` | image | `{"x":231.99,"y":114.0,"w":24.99,"h":42.0,"z":7200}` | `[]` |
| HR | Details | `z_32_234` | textbox | `{"x":256.98,"y":114.0,"w":114.02,"h":42.0,"z":2600}` | `[]` |
| HR | Details | `z_33_236` | slicer | `{"x":231.99,"y":156.0,"w":139.01,"h":48.0,"z":7300}` | `[{"field": "HumanResources.Full Name"}]` |
| HR | Details | `z_34_237` | slicer | `{"x":231.99,"y":204.0,"w":139.01,"h":48.0,"z":7400}` | `[{"field": "HumanResources.Gender"}]` |
| HR | Details | `z_35_238` | slicer | `{"x":231.99,"y":252.0,"w":139.01,"h":48.0,"z":7500}` | `[{"field": "HumanResources.Age Groups"}]` |
| HR | Details | `z_36_239` | slicer | `{"x":231.99,"y":300.0,"w":139.01,"h":48.0,"z":7600}` | `[{"field": "HumanResources.Education Level"}]` |
| HR | Details | `z_37_216` | shape | `{"x":371.0,"y":114.0,"w":12.99,"h":43.0,"z":3100}` | `[]` |
| HR | Details | `z_38_252_shown` | image | `{"x":383.99,"y":114.0,"w":24.99,"h":42.0,"z":7700}` | `[]` |
| HR | Details | `z_38_252_hidden` | image | `{"x":383.99,"y":114.0,"w":24.99,"h":42.0,"z":7800}` | `[]` |
| HR | Details | `z_39_247` | textbox | `{"x":408.98,"y":114.0,"w":160.01,"h":42.0,"z":3400}` | `[]` |
| HR | Details | `z_40_250` | slicer | `{"x":383.99,"y":156.0,"w":185.0,"h":48.0,"z":7900}` | `[{"field": "HumanResources.Job Title"}]` |
| HR | Details | `z_41_251` | slicer | `{"x":383.99,"y":204.0,"w":185.0,"h":48.0,"z":8000}` | `[{"field": "HumanResources.Department"}]` |
| HR | Details | `z_42_256` | shape | `{"x":568.99,"y":114.0,"w":12.99,"h":43.0,"z":3700}` | `[]` |
| HR | Details | `z_43_261_shown` | image | `{"x":581.98,"y":114.0,"w":24.99,"h":42.0,"z":8100}` | `[]` |
| HR | Details | `z_43_261_hidden` | image | `{"x":581.98,"y":114.0,"w":24.99,"h":42.0,"z":8200}` | `[]` |
| HR | Details | `z_44_255` | textbox | `{"x":606.97,"y":114.0,"w":125.01,"h":42.0,"z":4000}` | `[]` |
| HR | Details | `z_45_258` | slicer | `{"x":581.98,"y":160.0,"w":150.0,"h":56.0,"z":8300}` | `[{"field": "HumanResources.Location"}]` |
| HR | Details | `z_46_259` | slicer | `{"x":581.98,"y":216.0,"w":150.0,"h":56.0,"z":8400}` | `[{"field": "HumanResources.State"}]` |
| HR | Details | `z_47_260` | slicer | `{"x":581.98,"y":272.0,"w":150.0,"h":56.0,"z":8500}` | `[{"field": "HumanResources.City"}]` |
| HR | Details | `z_48_262` | shape | `{"x":731.98,"y":114.0,"w":12.99,"h":43.0,"z":4400}` | `[]` |
| HR | Details | `z_49_268_shown` | image | `{"x":744.97,"y":114.0,"w":24.99,"h":42.0,"z":8600}` | `[]` |
| HR | Details | `z_49_268_hidden` | image | `{"x":744.97,"y":114.0,"w":24.99,"h":42.0,"z":8700}` | `[]` |
| HR | Details | `z_50_265` | textbox | `{"x":769.96,"y":114.0,"w":148.01,"h":42.0,"z":4700}` | `[]` |
| HR | Details | `z_51_267` | slicer | `{"x":744.97,"y":160.0,"w":173.0,"h":68.0,"z":8800}` | `[{"field": "HumanResources.Salary"}]` |
| HR | Details | `z_52_269` | shape | `{"x":917.97,"y":114.0,"w":12.99,"h":43.0,"z":4900}` | `[]` |
| HR | Details | `z_53_277_shown` | image | `{"x":930.96,"y":114.0,"w":24.99,"h":42.0,"z":8900}` | `[]` |
| HR | Details | `z_53_277_hidden` | image | `{"x":930.96,"y":114.0,"w":24.99,"h":42.0,"z":9000}` | `[]` |
| HR | Details | `z_54_272` | textbox | `{"x":955.95,"y":114.0,"w":193.52,"h":42.0,"z":5200}` | `[]` |
| HR | Details | `z_55_274` | slicer | `{"x":930.96,"y":160.0,"w":218.51,"h":56.0,"z":9100}` | `[{"field": "HumanResources.Status"}]` |
| HR | Details | `z_56_275` | slicer | `{"x":930.96,"y":216.0,"w":218.51,"h":56.0,"z":9200}` | `[{"field": "HumanResources.Hiredate (Year)"}]` |
| HR | Details | `z_57_276` | slicer | `{"x":930.96,"y":272.0,"w":218.51,"h":56.0,"z":9300}` | `[{"field": "HumanResources.Termdate (Year)"}]` |
| HR | Details | `z_58_279` | shape | `{"x":1149.47,"y":114.0,"w":12.99,"h":43.0,"z":5600}` | `[]` |
| HR | Details | `z_59_285_shown` | image | `{"x":1162.46,"y":114.0,"w":24.99,"h":42.0,"z":9400}` | `[]` |
| HR | Details | `z_59_285_hidden` | image | `{"x":1162.46,"y":114.0,"w":24.99,"h":42.0,"z":9500}` | `[]` |
| HR | Details | `z_60_282` | textbox | `{"x":1187.45,"y":114.0,"w":185.53,"h":42.0,"z":5900}` | `[]` |
| HR | Details | `z_61_284` | slicer | `{"x":1162.46,"y":160.0,"w":210.52,"h":68.0,"z":9600}` | `[{"field": "HumanResources.Length of Hire"}]` |
| HR | Details | `z_62_217` | native | `{"x":117.0,"y":167.0,"w":1256.0,"h":606.0,"z":9700}` | `[{"role": "Values", "field": "HumanResources.Employee_ID"}, {"role": "Values", "field": "HumanResources.Full Name"}, {"role": "Values", "field": "HumanResources.Education Level"}, {"role": "Values", "field": "HumanResources.Job Title"}, {"role": "Values", "field": "HumanResources.Department"}, {"role": "Values", "field": "HumanResources.State"}, {"role": "Values", "field": "HumanResources.City"}, {"role": "Values", "field": "HumanResources.Status"}, {"role": "Values", "field": "HumanResources.Hiredate"}, {"role": "Values", "field": "HumanResources.Termdate"}, {"role": "Values", "field": "HumanResources.Gender"}, {"role": "Values", "field": "HumanResources.Location"}, {"role": "Values", "field": "HumanResources.Age Groups"}, {"role": "Values", "field": "HumanResources.Hiredate (Year)"}, {"role": "Values", "field": "HumanResources.Termdate (Year)"}, {"role": "Values", "field": "HumanResources.SUM Length of Hire"}, {"role": "Values", "field": "HumanResources.SUM Age"}, {"role": "Values", "field": "HumanResources.SUM Salary"}]` |
| HR | Details | `z_64_139` | textbox | `{"x":90.01,"y":240.0,"w":1309.0,"h":320.0,"z":6200}` | `[]` |
| HR | Details | `z_66_293` | shape | `{"x":23.0,"y":205.0,"w":6.01,"h":40.0,"z":6300}` | `[]` |

## Duplicate-key conflicts

- None.
