# Tableau migration report: HR Dashboard

## Tables and extracted rows

| Table | Hyper table | Rows | Columns |
|---|---|---:|---:|
| HumanResources | `Extract` | 8950 | 14 |

## Relationships


## Calculations

| Caption | Class | Status | DAX / reason |
|---|---|---|---|
| % Total Terminated | table_calc | table_calc | `` |
| % Total Hired | table_calc | table_calc | `` |
| Rank Top 2 | table_calc | table_calc | `` |
| Status | row | supported | `IF(ISBLANK('HumanResources'[Termdate]), "Hired", "Terminated")` |
| Highlight Max | table_calc | table_calc | `` |
| Total Hired | aggregate | supported | `COUNT('HumanResources'[Employee_ID])` |
| Total Terminated | aggregate | supported | `COUNTX('HumanResources', IF(NOT(ISBLANK('HumanResources'[Termdate])), 'HumanResources'[Employee_ID]))` |
| Total Active | aggregate | supported | `COUNTX('HumanResources', IF(ISBLANK('HumanResources'[Termdate]), 'HumanResources'[Employee_ID]))` |
| Location | row | supported | `SWITCH('HumanResources'[State], "New York", "HQ", "Branch")` |
| Age | row | unsupported | `Unsupported function DATEDIFF` |
| Age Groups | row | supported | `IF(('HumanResources'[Age] < 25), ">25", IF((('HumanResources'[Age] >= 25) && ('HumanResources'[Age] < 35)), "25-34", IF((('HumanResources'[Age] >= 35) && ('HumanResources'[Age] < 45)), "35-44", IF((('HumanResources'[Age] >= 45) && ('HumanResources'[Age] < 55)), "45-54", IF(('HumanResources'[Age] >= 55), "55+", BLANK())))))` |
| Full Name | row | supported | `(('HumanResources'[First Name] + " ") + 'HumanResources'[Last Name])` |
| Length of Hire | row | unsupported | `Unsupported function DATEDIFF` |
| % Highlight Max | table_calc | table_calc | `` |
| Rank Top 1 | table_calc | table_calc | `` |

## Auto measures

- **AVG Salary**: `AVERAGE('HumanResources'[Salary])`
- **AVG Age**: `AVERAGE('HumanResources'[Age])`
- **Length of Hire**: `SUM('HumanResources'[Length of Hire])`
- **Age**: `SUM('HumanResources'[Age])`
- **Salary**: `SUM('HumanResources'[Salary])`

## Lead overrides

- None.

## Visuals

| Dashboard | ID | Type | Position | Fields |
|---|---|---|---|---|
| HR | Summary | `z_0_228` | image | `{"x":0.0,"y":0.0,"w":1400.0,"h":800.0,"z":0}` | `[]` |
| HR | Summary | `z_1_133` | image | `{"x":20.01,"y":20.0,"w":69.99,"h":55.0,"z":100}` | `[]` |
| HR | Summary | `z_2_147` | textbox | `{"x":30.0,"y":85.0,"w":49.99,"h":73.33,"z":200}` | `[]` |
| HR | Summary | `z_3_135` | textbox | `{"x":30.0,"y":158.33,"w":49.99,"h":38.0,"z":300}` | `[]` |
| HR | Summary | `z_4_157` | textbox | `{"x":30.0,"y":196.33,"w":49.99,"h":10.0,"z":400}` | `[]` |
| HR | Summary | `z_5_136` | textbox | `{"x":30.0,"y":206.33,"w":49.99,"h":38.0,"z":500}` | `[]` |
| HR | Summary | `z_6_148` | textbox | `{"x":30.0,"y":244.33,"w":49.99,"h":73.33,"z":600}` | `[]` |
| HR | Summary | `z_7_151` | textbox | `{"x":30.0,"y":317.66,"w":49.99,"h":20.0,"z":700}` | `[]` |
| HR | Summary | `z_8_152` | textbox | `{"x":30.0,"y":337.66,"w":49.99,"h":11.0,"z":800}` | `[]` |
| HR | Summary | `z_9_141` | textbox | `{"x":30.0,"y":348.66,"w":49.99,"h":30.0,"z":900}` | `[]` |
| HR | Summary | `z_10_149` | textbox | `{"x":30.0,"y":378.66,"w":49.99,"h":73.33,"z":1000}` | `[]` |
| HR | Summary | `z_11_153` | textbox | `{"x":30.0,"y":451.98,"w":49.99,"h":20.0,"z":1100}` | `[]` |
| HR | Summary | `z_12_154` | textbox | `{"x":30.0,"y":471.98,"w":49.99,"h":11.0,"z":1200}` | `[]` |
| HR | Summary | `z_13_142` | textbox | `{"x":30.0,"y":482.98,"w":49.99,"h":38.0,"z":1300}` | `[]` |
| HR | Summary | `z_14_158` | textbox | `{"x":30.0,"y":520.98,"w":49.99,"h":10.0,"z":1400}` | `[]` |
| HR | Summary | `z_15_143` | textbox | `{"x":30.0,"y":530.98,"w":49.99,"h":38.0,"z":1500}` | `[]` |
| HR | Summary | `z_16_150` | textbox | `{"x":30.0,"y":568.98,"w":49.99,"h":60.0,"z":1600}` | `[]` |
| HR | Summary | `z_17_155` | textbox | `{"x":30.0,"y":628.98,"w":49.99,"h":20.0,"z":1700}` | `[]` |
| HR | Summary | `z_18_156` | textbox | `{"x":30.0,"y":648.98,"w":49.99,"h":11.0,"z":1800}` | `[]` |
| HR | Summary | `z_19_144` | image | `{"x":30.0,"y":659.98,"w":49.99,"h":25.0,"z":1900}` | `[]` |
| HR | Summary | `z_20_159` | textbox | `{"x":30.0,"y":684.98,"w":49.99,"h":10.0,"z":2000}` | `[]` |
| HR | Summary | `z_21_145` | image | `{"x":30.0,"y":694.98,"w":49.99,"h":30.0,"z":2100}` | `[]` |
| HR | Summary | `z_22_160` | textbox | `{"x":30.0,"y":724.98,"w":49.99,"h":10.0,"z":2200}` | `[]` |
| HR | Summary | `z_23_146` | image | `{"x":30.0,"y":734.98,"w":49.99,"h":30.02,"z":2300}` | `[]` |
| HR | Summary | `z_24_13` | textbox | `{"x":110.0,"y":0.0,"w":675.0,"h":70.0,"z":2400}` | `[]` |
| HR | Summary | `z_25_14` | textbox | `{"x":784.99,"y":0.0,"w":595.0,"h":70.0,"z":2500}` | `[]` |
| HR | Summary | `z_26_19` | textbox | `{"x":117.0,"y":77.0,"w":381.99,"h":31.0,"z":2600}` | `[]` |
| HR | Summary | `z_27_42` | textbox | `{"x":117.0,"y":108.0,"w":381.99,"h":28.0,"z":2700}` | `[]` |
| HR | Summary | `z_28_43` | textbox | `{"x":117.0,"y":136.0,"w":381.99,"h":43.0,"z":2800}` | `[]` |
| HR | Summary | `z_29_44` | textbox | `{"x":117.0,"y":179.0,"w":381.99,"h":1.0,"z":2900}` | `[]` |
| HR | Summary | `z_30_49` | textbox | `{"x":117.0,"y":185.0,"w":187.0,"h":22.0,"z":3000}` | `[]` |
| HR | Summary | `z_31_50` | textbox | `{"x":117.0,"y":207.0,"w":187.0,"h":49.0,"z":3100}` | `[]` |
| HR | Summary | `z_32_51` | native | `{"x":117.0,"y":256.0,"w":187.0,"h":70.0,"z":3200}` | `[{"role": "Category", "field": "HumanResources.Hiredate (Year)"}, {"role": "Y", "field": "HumanResources.Total Hired"}]` |
| HR | Summary | `z_33_47` | textbox | `{"x":304.0,"y":185.0,"w":1,"h":141.0,"z":3300}` | `[]` |
| HR | Summary | `z_34_53` | textbox | `{"x":304.99,"y":185.0,"w":193.9,"h":22.0,"z":3400}` | `[]` |
| HR | Summary | `z_35_54` | textbox | `{"x":304.99,"y":207.0,"w":193.9,"h":49.0,"z":3500}` | `[]` |
| HR | Summary | `z_36_55` | native | `{"x":304.99,"y":256.0,"w":193.9,"h":70.0,"z":3600}` | `[{"role": "Category", "field": "HumanResources.Termdate (Year)"}, {"role": "Y", "field": "HumanResources.Total Terminated"}]` |
| HR | Summary | `z_37_58` | textbox | `{"x":126.99,"y":336.0,"w":123.33,"h":30.0,"z":3700}` | `[]` |
| HR | Summary | `z_38_57` | textbox | `{"x":250.32,"y":336.0,"w":115.32,"h":30.0,"z":3800}` | `[]` |
| HR | Summary | `z_39_59` | textbox | `{"x":365.64,"y":336.0,"w":123.33,"h":30.0,"z":3900}` | `[]` |
| HR | Summary | `z_40_60` | textbox | `{"x":117.0,"y":366.0,"w":381.99,"h":173.99,"z":4000}` | `[]` |
| HR | Summary | `z_41_63` | textbox | `{"x":126.99,"y":544.99,"w":124.66,"h":30.0,"z":4100}` | `[]` |
| HR | Summary | `z_42_62` | textbox | `{"x":251.65,"y":544.99,"w":112.66,"h":30.0,"z":4200}` | `[]` |
| HR | Summary | `z_43_64` | textbox | `{"x":364.31,"y":544.99,"w":124.66,"h":30.0,"z":4300}` | `[]` |
| HR | Summary | `z_44_67` | textbox | `{"x":117.0,"y":574.99,"w":287.0,"h":200.01,"z":4400}` | `[]` |
| HR | Summary | `z_45_66` | textbox | `{"x":404.0,"y":574.99,"w":94.98,"h":200.01,"z":4500}` | `[]` |
| HR | Summary | `z_46_25` | textbox | `{"x":532.99,"y":77.0,"w":840.0,"h":31.0,"z":4600}` | `[]` |
| HR | Summary | `z_47_71` | textbox | `{"x":532.99,"y":113.0,"w":152.0,"h":26.0,"z":4700}` | `[]` |
| HR | Summary | `z_48_72` | textbox | `{"x":532.99,"y":139.0,"w":152.0,"h":268.99,"z":4800}` | `[]` |
| HR | Summary | `z_49_31` | textbox | `{"x":689.99,"y":113.0,"w":1,"h":295.0,"z":4900}` | `[]` |
| HR | Summary | `z_50_74` | textbox | `{"x":695.98,"y":113.0,"w":348.0,"h":26.0,"z":5000}` | `[]` |
| HR | Summary | `z_51_78` | textbox | `{"x":695.98,"y":139.0,"w":348.0,"h":70.0,"z":5100}` | `[]` |
| HR | Summary | `z_52_77` | textbox | `{"x":695.98,"y":209.0,"w":273.0,"h":199.0,"z":5200}` | `[]` |
| HR | Summary | `z_53_75` | textbox | `{"x":968.98,"y":209.0,"w":70.99,"h":199.0,"z":5300}` | `[]` |
| HR | Summary | `z_54_79` | textbox | `{"x":1048.98,"y":113.0,"w":1,"h":295.0,"z":5400}` | `[]` |
| HR | Summary | `z_55_81` | textbox | `{"x":1054.97,"y":113.0,"w":317.98,"h":26.0,"z":5500}` | `[]` |
| HR | Summary | `z_56_82` | textbox | `{"x":1054.97,"y":139.0,"w":317.98,"h":268.99,"z":5600}` | `[]` |
| HR | Summary | `z_57_28` | textbox | `{"x":532.99,"y":459.0,"w":840.0,"h":31.0,"z":5700}` | `[]` |
| HR | Summary | `z_58_84` | textbox | `{"x":532.99,"y":495.0,"w":416.01,"h":26.0,"z":5800}` | `[]` |
| HR | Summary | `z_59_85` | native | `{"x":532.99,"y":521.0,"w":416.01,"h":253.98,"z":5900}` | `[{"role": "Category", "field": "HumanResources.Education Level"}, {"role": "Y", "field": "HumanResources.AVG Salary"}, {"role": "Series", "field": "HumanResources.Gender"}]` |
| HR | Summary | `z_60_34` | textbox | `{"x":954.0,"y":495.0,"w":1,"h":280.0,"z":6000}` | `[]` |
| HR | Summary | `z_61_87` | textbox | `{"x":959.99,"y":495.0,"w":413.0,"h":26.0,"z":6100}` | `[]` |
| HR | Summary | `z_62_88` | textbox | `{"x":959.99,"y":521.0,"w":413.0,"h":254.0,"z":6200}` | `[]` |
| HR | Summary | `z_63_121` | textbox | `{"x":433.01,"y":77.0,"w":84.99,"h":32.0,"z":6300}` | `[]` |
| HR | Summary | `z_64_123` | slicer | `{"x":749.99,"y":9.0,"w":142.0,"h":51.0,"z":6400}` | `[{"field": "HumanResources.Gender"}]` |
| HR | Summary | `z_65_124` | slicer | `{"x":892.0,"y":9.0,"w":142.0,"h":51.0,"z":6500}` | `[{"field": "HumanResources.Status"}]` |
| HR | Summary | `z_66_125` | slicer | `{"x":1034.0,"y":9.0,"w":142.0,"h":51.0,"z":6600}` | `[{"field": "HumanResources.Location"}]` |
| HR | Summary | `z_67_126` | slicer | `{"x":1176.0,"y":9.0,"w":142.0,"h":51.0,"z":6700}` | `[{"field": "HumanResources.Hiredate (Year)"}]` |
| HR | Summary | `z_68_127` | textbox | `{"x":1329.01,"y":25.0,"w":51.0,"h":48.0,"z":6800}` | `[]` |
| HR | Summary | `z_69_138` | textbox | `{"x":90.01,"y":0.0,"w":1309.0,"h":240.0,"z":6900}` | `[]` |
| HR | Summary | `z_70_139` | textbox | `{"x":90.01,"y":240.0,"w":1309.0,"h":320.0,"z":7000}` | `[]` |
| HR | Summary | `z_71_140` | textbox | `{"x":90.01,"y":560.0,"w":1309.0,"h":240.0,"z":7100}` | `[]` |
| HR | Summary | `z_72_161` | textbox | `{"x":1319.0,"y":10.0,"w":70.99,"h":30.0,"z":7200}` | `[]` |
| HR | Summary | `z_73_223` | textbox | `{"x":23.0,"y":158.0,"w":6.01,"h":40.0,"z":7300}` | `[]` |
| HR | Details | `z_0_300` | image | `{"x":0.0,"y":0.0,"w":1400.0,"h":800.0,"z":0}` | `[]` |
| HR | Details | `z_1_133` | image | `{"x":20.01,"y":20.0,"w":69.99,"h":55.0,"z":100}` | `[]` |
| HR | Details | `z_2_147` | textbox | `{"x":30.0,"y":85.0,"w":49.99,"h":73.33,"z":200}` | `[]` |
| HR | Details | `z_3_135` | textbox | `{"x":30.0,"y":158.33,"w":49.99,"h":38.0,"z":300}` | `[]` |
| HR | Details | `z_4_157` | textbox | `{"x":30.0,"y":196.33,"w":49.99,"h":10.0,"z":400}` | `[]` |
| HR | Details | `z_5_136` | textbox | `{"x":30.0,"y":206.33,"w":49.99,"h":38.0,"z":500}` | `[]` |
| HR | Details | `z_6_148` | textbox | `{"x":30.0,"y":244.33,"w":49.99,"h":73.33,"z":600}` | `[]` |
| HR | Details | `z_7_151` | textbox | `{"x":30.0,"y":317.66,"w":49.99,"h":20.0,"z":700}` | `[]` |
| HR | Details | `z_8_152` | textbox | `{"x":30.0,"y":337.66,"w":49.99,"h":11.0,"z":800}` | `[]` |
| HR | Details | `z_9_141` | textbox | `{"x":30.0,"y":348.66,"w":49.99,"h":30.0,"z":900}` | `[]` |
| HR | Details | `z_10_149` | textbox | `{"x":30.0,"y":378.66,"w":49.99,"h":73.33,"z":1000}` | `[]` |
| HR | Details | `z_11_153` | textbox | `{"x":30.0,"y":451.98,"w":49.99,"h":20.0,"z":1100}` | `[]` |
| HR | Details | `z_12_154` | textbox | `{"x":30.0,"y":471.98,"w":49.99,"h":11.0,"z":1200}` | `[]` |
| HR | Details | `z_13_142` | textbox | `{"x":30.0,"y":482.98,"w":49.99,"h":38.0,"z":1300}` | `[]` |
| HR | Details | `z_14_158` | textbox | `{"x":30.0,"y":520.98,"w":49.99,"h":10.0,"z":1400}` | `[]` |
| HR | Details | `z_15_143` | textbox | `{"x":30.0,"y":530.98,"w":49.99,"h":38.0,"z":1500}` | `[]` |
| HR | Details | `z_16_150` | textbox | `{"x":30.0,"y":568.98,"w":49.99,"h":60.0,"z":1600}` | `[]` |
| HR | Details | `z_17_155` | textbox | `{"x":30.0,"y":628.98,"w":49.99,"h":20.0,"z":1700}` | `[]` |
| HR | Details | `z_18_156` | textbox | `{"x":30.0,"y":648.98,"w":49.99,"h":11.0,"z":1800}` | `[]` |
| HR | Details | `z_19_144` | image | `{"x":30.0,"y":659.98,"w":49.99,"h":25.0,"z":1900}` | `[]` |
| HR | Details | `z_20_159` | textbox | `{"x":30.0,"y":684.98,"w":49.99,"h":10.0,"z":2000}` | `[]` |
| HR | Details | `z_21_145` | image | `{"x":30.0,"y":694.98,"w":49.99,"h":30.0,"z":2100}` | `[]` |
| HR | Details | `z_22_160` | textbox | `{"x":30.0,"y":724.98,"w":49.99,"h":10.0,"z":2200}` | `[]` |
| HR | Details | `z_23_146` | image | `{"x":30.0,"y":734.98,"w":49.99,"h":30.02,"z":2300}` | `[]` |
| HR | Details | `z_24_13` | textbox | `{"x":110.0,"y":0.0,"w":672.99,"h":70.0,"z":2400}` | `[]` |
| HR | Details | `z_25_14` | textbox | `{"x":782.99,"y":0.0,"w":597.0,"h":70.0,"z":2500}` | `[]` |
| HR | Details | `z_26_292` | textbox | `{"x":117.0,"y":77.0,"w":1256.0,"h":37.0,"z":2600}` | `[]` |
| HR | Details | `z_27_226` | textbox | `{"x":117.0,"y":114.0,"w":24.99,"h":43.0,"z":2700}` | `[]` |
| HR | Details | `z_28_222` | textbox | `{"x":141.99,"y":114.0,"w":77.01,"h":43.0,"z":2800}` | `[]` |
| HR | Details | `z_29_227` | slicer | `{"x":117.0,"y":161.0,"w":102.0,"h":53.0,"z":2900}` | `[{"field": "HumanResources.Employee_ID"}]` |
| HR | Details | `z_30_215` | textbox | `{"x":219.0,"y":114.0,"w":12.99,"h":43.0,"z":3000}` | `[]` |
| HR | Details | `z_31_240` | textbox | `{"x":231.99,"y":114.0,"w":24.99,"h":42.0,"z":3100}` | `[]` |
| HR | Details | `z_32_234` | textbox | `{"x":256.98,"y":114.0,"w":114.02,"h":42.0,"z":3200}` | `[]` |
| HR | Details | `z_33_236` | slicer | `{"x":231.99,"y":156.0,"w":139.01,"h":48.0,"z":3300}` | `[{"field": "HumanResources.Full Name"}]` |
| HR | Details | `z_34_237` | slicer | `{"x":231.99,"y":204.0,"w":139.01,"h":48.0,"z":3400}` | `[{"field": "HumanResources.Gender"}]` |
| HR | Details | `z_35_238` | slicer | `{"x":231.99,"y":252.0,"w":139.01,"h":48.0,"z":3500}` | `[{"field": "HumanResources.Age Groups"}]` |
| HR | Details | `z_36_239` | slicer | `{"x":231.99,"y":300.0,"w":139.01,"h":48.0,"z":3600}` | `[{"field": "HumanResources.Education Level"}]` |
| HR | Details | `z_37_216` | textbox | `{"x":371.0,"y":114.0,"w":12.99,"h":43.0,"z":3700}` | `[]` |
| HR | Details | `z_38_252` | textbox | `{"x":383.99,"y":114.0,"w":24.99,"h":42.0,"z":3800}` | `[]` |
| HR | Details | `z_39_247` | textbox | `{"x":408.98,"y":114.0,"w":160.01,"h":42.0,"z":3900}` | `[]` |
| HR | Details | `z_40_250` | slicer | `{"x":383.99,"y":156.0,"w":185.0,"h":48.0,"z":4000}` | `[{"field": "HumanResources.Job Title"}]` |
| HR | Details | `z_41_251` | slicer | `{"x":383.99,"y":204.0,"w":185.0,"h":48.0,"z":4100}` | `[{"field": "HumanResources.Department"}]` |
| HR | Details | `z_42_256` | textbox | `{"x":568.99,"y":114.0,"w":12.99,"h":43.0,"z":4200}` | `[]` |
| HR | Details | `z_43_261` | textbox | `{"x":581.98,"y":114.0,"w":24.99,"h":42.0,"z":4300}` | `[]` |
| HR | Details | `z_44_255` | textbox | `{"x":606.97,"y":114.0,"w":125.01,"h":42.0,"z":4400}` | `[]` |
| HR | Details | `z_45_258` | slicer | `{"x":581.98,"y":160.0,"w":150.0,"h":56.0,"z":4500}` | `[{"field": "HumanResources.Location"}]` |
| HR | Details | `z_46_259` | slicer | `{"x":581.98,"y":216.0,"w":150.0,"h":56.0,"z":4600}` | `[{"field": "HumanResources.State"}]` |
| HR | Details | `z_47_260` | slicer | `{"x":581.98,"y":272.0,"w":150.0,"h":56.0,"z":4700}` | `[{"field": "HumanResources.City"}]` |
| HR | Details | `z_48_262` | textbox | `{"x":731.98,"y":114.0,"w":12.99,"h":43.0,"z":4800}` | `[]` |
| HR | Details | `z_49_268` | textbox | `{"x":744.97,"y":114.0,"w":24.99,"h":42.0,"z":4900}` | `[]` |
| HR | Details | `z_50_265` | textbox | `{"x":769.96,"y":114.0,"w":148.01,"h":42.0,"z":5000}` | `[]` |
| HR | Details | `z_51_267` | slicer | `{"x":744.97,"y":160.0,"w":173.0,"h":68.0,"z":5100}` | `[{"field": "HumanResources.Salary"}]` |
| HR | Details | `z_52_269` | textbox | `{"x":917.97,"y":114.0,"w":12.99,"h":43.0,"z":5200}` | `[]` |
| HR | Details | `z_53_277` | textbox | `{"x":930.96,"y":114.0,"w":24.99,"h":42.0,"z":5300}` | `[]` |
| HR | Details | `z_54_272` | textbox | `{"x":955.95,"y":114.0,"w":193.52,"h":42.0,"z":5400}` | `[]` |
| HR | Details | `z_55_274` | slicer | `{"x":930.96,"y":160.0,"w":218.51,"h":56.0,"z":5500}` | `[{"field": "HumanResources.Status"}]` |
| HR | Details | `z_56_275` | slicer | `{"x":930.96,"y":216.0,"w":218.51,"h":56.0,"z":5600}` | `[{"field": "HumanResources.Hiredate (Year)"}]` |
| HR | Details | `z_57_276` | slicer | `{"x":930.96,"y":272.0,"w":218.51,"h":56.0,"z":5700}` | `[{"field": "HumanResources.Termdate (Year)"}]` |
| HR | Details | `z_58_279` | textbox | `{"x":1149.47,"y":114.0,"w":12.99,"h":43.0,"z":5800}` | `[]` |
| HR | Details | `z_59_285` | textbox | `{"x":1162.46,"y":114.0,"w":24.99,"h":42.0,"z":5900}` | `[]` |
| HR | Details | `z_60_282` | textbox | `{"x":1187.45,"y":114.0,"w":185.53,"h":42.0,"z":6000}` | `[]` |
| HR | Details | `z_61_284` | textbox | `{"x":1162.46,"y":160.0,"w":210.52,"h":68.0,"z":6100}` | `[]` |
| HR | Details | `z_62_217` | textbox | `{"x":117.0,"y":167.0,"w":1256.0,"h":606.0,"z":6200}` | `[]` |
| HR | Details | `z_63_294` | textbox | `{"x":90.01,"y":0.0,"w":1309.0,"h":240.0,"z":6300}` | `[]` |
| HR | Details | `z_64_139` | textbox | `{"x":90.01,"y":240.0,"w":1309.0,"h":320.0,"z":6400}` | `[]` |
| HR | Details | `z_65_295` | textbox | `{"x":90.01,"y":560.0,"w":1309.0,"h":240.0,"z":6500}` | `[]` |
| HR | Details | `z_66_293` | textbox | `{"x":23.0,"y":205.0,"w":6.01,"h":40.0,"z":6600}` | `[]` |

## Duplicate-key conflicts

- None.
