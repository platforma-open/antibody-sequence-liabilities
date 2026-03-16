import type {
  PlDataTableStateV2,
  PlRef,
} from '@platforma-sdk/model';
import {
  BlockModel,
  createPlDataTableStateV2,
  createPlDataTableV2,
} from '@platforma-sdk/model';
import { getDefaultBlockLabel } from './label';

export type CustomLiability = {
  name: string;
  pattern: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  fixability: 'easily_fixable' | 'fixable' | 'hard_to_fix';
  regions: string[];
};

export type BlockArgs = {
  defaultBlockLabel: string;
  customBlockLabel: string;
  inputAnchor?: PlRef;
  liabilityTypes?: string[];
  customLiabilities?: CustomLiability[];
};

export type UiState = {
  tableState: PlDataTableStateV2;
};

export const liabilityTypes: {
  value: string;
  label: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  fixability: 'easily_fixable' | 'fixable' | 'hard_to_fix' | 'structural';
}[] = [
  { value: 'Deamidation (N[GS])', label: 'Deamidation (N[GS])', riskLevel: 'High', fixability: 'hard_to_fix' },
  { value: 'Fragmentation (DP)', label: 'Fragmentation (DP)', riskLevel: 'High', fixability: 'hard_to_fix' },
  { value: 'Isomerization (D[DGHST])', label: 'Isomerization (D[DGHST])', riskLevel: 'High', fixability: 'hard_to_fix' },
  { value: 'N-linked Glycosylation (N[^P][ST])', label: 'N-linked Glycosylation (N[^P][ST])', riskLevel: 'High', fixability: 'hard_to_fix' },
  { value: 'Deamidation (N[AHNT])', label: 'Deamidation (N[AHNT])', riskLevel: 'Medium', fixability: 'fixable' },
  { value: 'Hydrolysis (NP)', label: 'Hydrolysis (NP)', riskLevel: 'Medium', fixability: 'fixable' },
  { value: 'Fragmentation (TS)', label: 'Fragmentation (TS)', riskLevel: 'Medium', fixability: 'fixable' },
  { value: 'Tryptophan Oxidation (W)', label: 'Tryptophan Oxidation (W)', riskLevel: 'Medium', fixability: 'easily_fixable' },
  { value: 'Methionine Oxidation (M)', label: 'Methionine Oxidation (M)', riskLevel: 'Medium', fixability: 'easily_fixable' },
  { value: 'Deamidation ([STK]N)', label: 'Deamidation ([STK]N)', riskLevel: 'Low', fixability: 'easily_fixable' },
  { value: 'Missing Cysteines', label: 'Missing Cysteines', riskLevel: 'High', fixability: 'structural' },
  { value: 'Extra Cysteines', label: 'Extra Cysteines', riskLevel: 'High', fixability: 'structural' },
];

export const model = BlockModel.create()
  .withArgs<BlockArgs>({
    defaultBlockLabel: getDefaultBlockLabel({
      liabilityTypes: liabilityTypes.map((liabilityType) => liabilityType.value),
      allLiabilityTypes: liabilityTypes.map((liabilityType) => liabilityType.value),
    }),
    customBlockLabel: '',
    liabilityTypes: liabilityTypes.map((liabilityType) => liabilityType.value),
    customLiabilities: [],
  })

  .withUiState<UiState>({
    tableState: createPlDataTableStateV2(),
  })

  .argsValid((ctx) => {
    if (ctx.args.inputAnchor === undefined) return false;
    const customs = ctx.args.customLiabilities ?? [];
    const names = customs.map((c) => c.name);
    if (names.length !== new Set(names).size) return false;
    for (const c of customs) {
      if (!c.name || !c.pattern) return false;
      try {
        new RegExp(c.pattern);
      } catch {
        return false;
      }
    }
    return true;
  })

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

  .outputWithStatus('pt', (ctx) => {
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
    const qualityColumn = pCols.find((p) => p.spec.name === 'pl7.app/vdj/sequenceQuality');
    if (qualityColumn === undefined) {
      return undefined;
    }
    return ctx.createPTable({ columns: [qualityColumn] });
  })

  .output('isRunning', (ctx) => ctx.outputs?.getIsReadyOrError() === false)

  .title(() => 'Antibody Sequence Liabilities')

  .subtitle((ctx) => ctx.args.customBlockLabel || ctx.args.defaultBlockLabel)

  .sections((_) => [
    { type: 'link', href: '/', label: 'Table' },
  ])

  .done(2);

export { getDefaultBlockLabel } from './label';
