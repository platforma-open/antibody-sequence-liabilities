import type {
  InferOutputsType,
  PlDataTableStateV2,
  PlRef,
} from '@platforma-sdk/model';
import {
  BlockModel,
  createPlDataTableStateV2,
  createPlDataTableV2,
} from '@platforma-sdk/model';

export type BlockArgs = {
  inputAnchor?: PlRef;
  liabilityTypes?: string[];
};

export type UiState = {
  title: string;
  tableState: PlDataTableStateV2;
};

export const liabilityTypes = [
  { value: 'Deamidation (N[GS])', label: 'Deamidation (N[GS])' },
  { value: 'Fragmentation (DP)', label: 'Fragmentation (DP)' },
  { value: 'Isomerization (D[DGHST])', label: 'Isomerization (D[DGHST])' },
  { value: 'N-linked Glycosylation (N[^P][ST])', label: 'N-linked Glycosylation (N[^P][ST])' },
  { value: 'Deamidation (N[AHNT])', label: 'Deamidation (N[AHNT])' },
  { value: 'Hydrolysis (NP)', label: 'Hydrolysis (NP)' },
  { value: 'Fragmentation (TS)', label: 'Fragmentation (TS)' },
  { value: 'Tryptophan Oxidation (W)', label: 'Tryptophan Oxidation (W)' },
  { value: 'Methionine Oxidation (M)', label: 'Methionine Oxidation (M)' },
  { value: 'Deamidation ([STK]N)', label: 'Deamidation ([STK]N)' },
  { value: 'Missing Cysteines', label: 'Missing Cysteines' },
  { value: 'Extra Cysteines', label: 'Extra Cysteines' },
];

export const model = BlockModel.create()
  .withArgs<BlockArgs>({
    liabilityTypes: liabilityTypes.map((liabilityType) => liabilityType.value),
  })

  .withUiState<UiState>({
    title: 'Antibody Sequence Liabilities',
    tableState: createPlDataTableStateV2(),
  })

  .argsValid((ctx) => ctx.args.inputAnchor !== undefined)

  .output('inputOptions', (ctx) =>
    ctx.resultPool.getOptions([{
      axes: [
        { name: 'pl7.app/sampleId' },
        { name: 'pl7.app/vdj/clonotypeKey' },
      ],
      annotations: { 'pl7.app/isAnchor': 'true' },
    }, {
      axes: [
        { name: 'pl7.app/sampleId' },
        { name: 'pl7.app/vdj/scClonotypeKey' },
      ],
      annotations: { 'pl7.app/isAnchor': 'true' },
    }]),
  )

  .output('pt', (ctx) => {
    const pCols = ctx.outputs?.resolve('outputLiabilities')?.getPColumns();
    if (pCols === undefined) {
      return undefined;
    }
    return createPlDataTableV2(
      ctx,
      pCols,
      ctx.uiState.tableState,
    );
  })

  .output('liabilitiesRiskTable', (ctx) => {
    const pCols = ctx.outputs?.resolve('outputLiabilities')?.getPColumns();
    if (pCols === undefined) {
      return undefined;
    }
    const riskColumn = pCols.find((p) => p.spec.name === 'pl7.app/vdj/liabilitiesRisk');
    if (riskColumn === undefined) {
      return undefined;
    }
    return ctx.createPTable({ columns: [riskColumn] });
  })

  .output('isRunning', (ctx) => ctx.outputs?.getIsReadyOrError() === false)

  .title((ctx) => ctx.uiState.title)

  .sections((_) => [
    { type: 'link', href: '/', label: 'Table' },
  ])

  .done();

export type BlockOutputs = InferOutputsType<typeof model>;
