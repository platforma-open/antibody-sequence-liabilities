import type {
  PlRef,
  InferOutputsType,
} from '@platforma-sdk/model';
import {
  BlockModel,
  createPlDataTable,
  isPColumn,
  createPlDataTableSheet,
  getUniquePartitionKeys,
  PlDataTableState,
} from '@platforma-sdk/model';

export type BlockArgs = {
  inputAnchor?: PlRef;
  clonotypingRunId?: string;
  chain?: string;
  title?: string;
};

export type UiState = {
  blockTitle: string;
  tableState?: PlDataTableState;
};

export const model = BlockModel.create()
  .withArgs({ inputAnchor: undefined, clonotypingRunId: undefined, chain: undefined, title: undefined })

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
    
    //const upstream = ctx.resultPool 
    //  .getData()
    //  .entries.map((v) => v.obj)
    //  .filter(isPColumn)
    //  .filter((column) => column.spec.domain?.["pl7.app/vdj/clonotypingRunId"] === ctx.args.clonotypingRunId)
    //  .filter((column) => column.spec.domain?.["pl7.app/vdj/chain"] === ctx.args.chain)
    //  .filter((column) => column.spec.domain?.["pl7.app/alphabet"] === "aminoacid")
    //  .filter((column) => column.spec.domain?.["pl7.app/vdj/feature"] === "CDR3");

    //pCols.push(...upstream);

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
