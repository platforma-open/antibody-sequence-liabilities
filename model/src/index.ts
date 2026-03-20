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
  usePredefinedLiabilities?: boolean;
  disabledPredefinedLiabilities?: string[];
  customLiabilities?: CustomLiability[];
};

export type UiState = {
  tableState: PlDataTableStateV2;
};

export const liabilityTypes: {
  value: string;
  label: string;
  pattern: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  fixability: 'easily_fixable' | 'fixable' | 'hard_to_fix' | 'structural';
  enabledByDefault: boolean;
}[] = [
  { value: 'Deamidation (N[GS])', label: 'Deamidation (N[GS])', pattern: 'N[GS]', riskLevel: 'High', fixability: 'fixable', enabledByDefault: true },
  { value: 'Fragmentation (DP)', label: 'Fragmentation (DP)', pattern: 'DP', riskLevel: 'High', fixability: 'fixable', enabledByDefault: true },
  { value: 'Isomerization (D[DGHST])', label: 'Isomerization (D[DGHST])', pattern: 'D[DGHST]', riskLevel: 'High', fixability: 'fixable', enabledByDefault: true },
  { value: 'N-linked Glycosylation (N[^P][ST])', label: 'N-linked Glycosylation (N[^P][ST])', pattern: 'N[^P][ST]', riskLevel: 'High', fixability: 'fixable', enabledByDefault: true },
  { value: 'Deamidation (N[AHNT])', label: 'Deamidation (N[AHNT])', pattern: 'N[AHNT]', riskLevel: 'Medium', fixability: 'easily_fixable', enabledByDefault: true },
  { value: 'Hydrolysis (NP)', label: 'Hydrolysis (NP)', pattern: 'NP', riskLevel: 'Medium', fixability: 'fixable', enabledByDefault: true },
  { value: 'Fragmentation (TS)', label: 'Fragmentation (TS)', pattern: 'TS', riskLevel: 'Medium', fixability: 'fixable', enabledByDefault: true },
  { value: 'Tryptophan Oxidation (W)', label: 'Tryptophan Oxidation (W)', pattern: 'W', riskLevel: 'Medium', fixability: 'easily_fixable', enabledByDefault: true },
  { value: 'Methionine Oxidation (M)', label: 'Methionine Oxidation (M)', pattern: 'M', riskLevel: 'Medium', fixability: 'easily_fixable', enabledByDefault: true },
  { value: 'Deamidation ([STK]N)', label: 'Deamidation ([STK]N)', pattern: '[STK]N', riskLevel: 'Low', fixability: 'easily_fixable', enabledByDefault: true },
  { value: 'Integrin binding', label: 'Integrin binding', pattern: 'RGD|RYD|KGD|NGR|LDV|DGE|GPR', riskLevel: 'Low', fixability: 'easily_fixable', enabledByDefault: false },
  { value: 'Missing Cysteines', label: 'Missing Cysteines', pattern: '—', riskLevel: 'High', fixability: 'structural', enabledByDefault: true },
  { value: 'Extra Cysteines', label: 'Extra Cysteines', pattern: '—', riskLevel: 'High', fixability: 'hard_to_fix', enabledByDefault: true },
];

export const model = BlockModel.create()
  .withArgs<BlockArgs>({
    defaultBlockLabel: getDefaultBlockLabel({
      usePredefinedLiabilities: true,
      disabledPredefinedLiabilities: liabilityTypes.filter((l) => !l.enabledByDefault).map((l) => l.value),
      allLiabilityTypes: liabilityTypes.map((liabilityType) => liabilityType.value),
    }),
    customBlockLabel: '',
    usePredefinedLiabilities: true,
    disabledPredefinedLiabilities: liabilityTypes.filter((l) => !l.enabledByDefault).map((l) => l.value),
    customLiabilities: [],
  })

  .withUiState<UiState>({
    tableState: createPlDataTableStateV2(),
  })

  .argsValid((ctx) => {
    if (ctx.args.inputAnchor === undefined) return false;
    const predefinedNames = new Set(liabilityTypes.map((l) => l.value));
    const customs = ctx.args.customLiabilities ?? [];
    const customNames = customs.map((c) => c.name);
    if (customNames.length !== new Set(customNames).size) return false;
    for (const c of customs) {
      if (!c.name || !c.pattern) return false;
      if (predefinedNames.has(c.name)) return false;
      try {
        new RegExp(c.pattern);
      } catch {
        return false;
      }
      if (!c.regions || c.regions.length === 0) return false;
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

  .output('isRunning', (ctx) => ctx.outputs?.getIsReadyOrError() === false)

  .title(() => 'Antibody Sequence Liabilities')

  .subtitle((ctx) => ctx.args.customBlockLabel || ctx.args.defaultBlockLabel)

  .sections((_) => [
    { type: 'link', href: '/', label: 'Table' },
  ])

  .done(2);

export { getDefaultBlockLabel } from './label';
