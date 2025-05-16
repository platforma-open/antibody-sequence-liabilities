import type {
  PlRef,
  InferOutputsType,
  PlDataTableState,
} from '@platforma-sdk/model';
import {
  BlockModel,
  createPlDataTable,
} from '@platforma-sdk/model';

export type BlockArgs = {
  inputAnchor?: PlRef;
  clonotypingRunId?: string;
  chain?: string;
  title?: string;
  liabilityTypes?: string[];
};

export type UiState = {
  blockTitle: string;
  tableState?: PlDataTableState;
};

export const model = BlockModel.create()
  .withArgs({ inputAnchor: undefined, title: undefined })

  .withUiState<UiState>({
    blockTitle: 'Antibody Sequence Liabilities',
    tableState: {
      gridState: {},
      pTableParams: {
        sorting: [],
        filters: [],
      },
    },
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
    return {
      table: createPlDataTable(ctx, pCols, ctx.uiState?.tableState),
    };
  })

  .title((ctx) => (ctx.args.title ? `Antibody Sequence Liabilities - ${ctx.args.title}` : 'Antibody Sequence Liabilities'))

  .sections((_) => [
    { type: 'link', href: '/', label: 'Table' },
  ])

  .done();

export type BlockOutputs = InferOutputsType<typeof model>;
