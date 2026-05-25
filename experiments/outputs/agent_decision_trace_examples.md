# Agent Workflow Dry-Run Decision Traces

Local runtime note:

- Agent roles are simulated sequentially.
- No concurrent LLM agents are used.
- Deterministic Python handles data transformation.
- LLM use is conceptual / prompt-governed at this stage.
- No model training, threshold tuning, external data download, or prediction-pipeline modification occurred.

## Dry-Run Case: Ubon Ratchathani 2022-W36

### Input Record Summary
- province: Ubon Ratchathani
- region: Northeast
- year/week: 2022 / 36
- source: local_prediction_outputs_no_label_decision_use

### Data Audit Agent
- status: pass
- notes: required fields present; corrected-label phase record

### Feature Agent
- status: pass
- notes: available families: weather/leaf wetness, host susceptibility, spatial/regional pressure, BUS reference

### Model Agent
- status: pass
- notes: route DNN core primary; DNN analog history second opinion; RF all analog ranking comparator

### Decision Governance Agent
- status: pass
- notes: policy=balanced default + regional second opinion + ranking comparator; tier=high alert; no threshold tuning; labels not used

### Regional Routing Agent
- status: pass
- notes: Northeast enhanced monitoring route

### Explanation Agent
- status: pass
- notes: humidity: high (88.6); leaf wet hours: high (98) | susceptibility: high (0.609) | neighbor blast: high (0.2); regional pressure: high (0.345) | DNN analog score: 0.493; RF analog rank score: 0.424 | Northeast enhanced monitoring; analog is similarity not direct spread

### Report Writer Agent
- status: pass
- notes: final dry-run alert record and markdown trace written

### Final Alert Record
- primary model: DNN no-class-weight core_no_BUS
- primary score: 0.699564
- alert tier: high alert
- selected policy: balanced default + regional second opinion + ranking comparator
- confidence: monitor disagreement
- recommended action: priority field check
- explanation: DNN no-class-weight core_no_BUS routed by region=Northeast; Northeast enhanced monitoring; analog is similarity not direct spread; labels not used for decision.

## Dry-Run Case: Tak 2022-W50

### Input Record Summary
- province: Tak
- region: North
- year/week: 2022 / 50
- source: local_prediction_outputs_no_label_decision_use

### Data Audit Agent
- status: pass
- notes: required fields present; corrected-label phase record

### Feature Agent
- status: pass
- notes: available families: weather/leaf wetness, host susceptibility, spatial/regional pressure, BUS reference

### Model Agent
- status: pass
- notes: route DNN core primary only with low-confidence caveat

### Decision Governance Agent
- status: pass
- notes: policy=balanced default + diagnostic backlog; tier=watch; no threshold tuning; labels not used

### Regional Routing Agent
- status: low_confidence
- notes: North diagnostic backlog route

### Explanation Agent
- status: pass
- notes: humidity: modest (71.3); leaf wet hours: modest (5) | susceptibility: modest (0.5) | neighbor blast: high (0.2); regional pressure: modest (0.0588) | DNN analog score: 0.105; RF analog rank score: 0.0749 | North low-confidence diagnostic backlog; do not force threshold lowering

### Report Writer Agent
- status: pass
- notes: final dry-run alert record and markdown trace written

### Final Alert Record
- primary model: DNN no-class-weight core_no_BUS
- primary score: 0.108726
- alert tier: watch
- selected policy: balanced default + diagnostic backlog
- confidence: low confidence
- recommended action: diagnostic review
- explanation: DNN no-class-weight core_no_BUS routed by region=North; North low-confidence diagnostic backlog; do not force threshold lowering; labels not used for decision.

## Dry-Run Case: Songkhla 2022-W17

### Input Record Summary
- province: Songkhla
- region: South
- year/week: 2022 / 17
- source: local_prediction_outputs_no_label_decision_use

### Data Audit Agent
- status: pass
- notes: required fields present; corrected-label phase record

### Feature Agent
- status: pass
- notes: available families: weather/leaf wetness, host susceptibility, spatial/regional pressure, BUS reference

### Model Agent
- status: pass
- notes: route DNN core primary; sparse-region caveat; RF comparator if available

### Decision Governance Agent
- status: pass
- notes: policy=balanced default + sparse-region caveat; tier=warning; no threshold tuning; labels not used

### Regional Routing Agent
- status: warning
- notes: South sparse-positive caveat

### Explanation Agent
- status: pass
- notes: humidity: high (81.1); leaf wet hours: high (65) | susceptibility: modest (0.501) | neighbor blast: modest (0); regional pressure: high (0.1) | DNN analog score: 0.171; RF analog rank score: 0.225 | South sparse-positive caveat

### Report Writer Agent
- status: pass
- notes: final dry-run alert record and markdown trace written

### Final Alert Record
- primary model: DNN no-class-weight core_no_BUS
- primary score: 0.3173
- alert tier: warning
- selected policy: balanced default + sparse-region caveat
- confidence: medium confidence
- recommended action: field monitoring
- explanation: DNN no-class-weight core_no_BUS routed by region=South; South sparse-positive caveat; labels not used for decision.

## Dry-Run Case: Phra Nakhon Si Ayutthaya 2022-W41

### Input Record Summary
- province: Phra Nakhon Si Ayutthaya
- region: Central
- year/week: 2022 / 41
- source: local_prediction_outputs_no_label_decision_use

### Data Audit Agent
- status: pass
- notes: required fields present; corrected-label phase record

### Feature Agent
- status: pass
- notes: available families: weather/leaf wetness, host susceptibility, spatial/regional pressure, BUS reference

### Model Agent
- status: pass
- notes: route DNN core primary; sparse-region caveat; RF comparator if available

### Decision Governance Agent
- status: pass
- notes: policy=balanced default + sparse-region caveat; tier=low risk; no threshold tuning; labels not used

### Regional Routing Agent
- status: warning
- notes: Central sparse-positive caveat

### Explanation Agent
- status: pass
- notes: humidity: modest (74.9); leaf wet hours: modest (23) | susceptibility: modest (0.501) | neighbor blast: modest (0); regional pressure: modest (0) | DNN analog score: 0.0582; RF analog rank score: 0.0647 | Central sparse-positive caveat

### Report Writer Agent
- status: pass
- notes: final dry-run alert record and markdown trace written

### Final Alert Record
- primary model: DNN no-class-weight core_no_BUS
- primary score: 0.056992
- alert tier: low risk
- selected policy: balanced default + sparse-region caveat
- confidence: medium-low confidence
- recommended action: diagnostic review
- explanation: DNN no-class-weight core_no_BUS routed by region=Central; Central sparse-positive caveat; labels not used for decision.

## Dry-Run Case: Buri Ram 2022-W36

### Input Record Summary
- province: Buri Ram
- region: Northeast
- year/week: 2022 / 36
- source: local_prediction_outputs_no_label_decision_use

### Data Audit Agent
- status: pass
- notes: required fields present; corrected-label phase record

### Feature Agent
- status: pass
- notes: available families: weather/leaf wetness, host susceptibility, spatial/regional pressure, BUS reference

### Model Agent
- status: pass
- notes: route DNN core primary; DNN analog history second opinion; RF all analog ranking comparator

### Decision Governance Agent
- status: pass
- notes: policy=calibrated alert tier dashboard + ranking comparator; tier=high alert; no threshold tuning; labels not used

### Regional Routing Agent
- status: pass
- notes: Northeast enhanced monitoring route

### Explanation Agent
- status: pass
- notes: humidity: high (90.4); leaf wet hours: high (82) | susceptibility: high (0.641) | neighbor blast: high (0.2); regional pressure: high (0.345) | DNN analog score: 0.445; RF analog rank score: 0.419 | Northeast enhanced monitoring; analog is similarity not direct spread

### Report Writer Agent
- status: pass
- notes: final dry-run alert record and markdown trace written

### Final Alert Record
- primary model: DNN no-class-weight core_no_BUS
- primary score: 0.625929
- alert tier: high alert
- selected policy: calibrated alert tier dashboard + ranking comparator
- confidence: monitor disagreement
- recommended action: priority field check
- explanation: DNN no-class-weight core_no_BUS routed by region=Northeast; Northeast enhanced monitoring; analog is similarity not direct spread; labels not used for decision.
