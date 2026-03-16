import type { BlockArgs } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import { liabilityTypes } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import type { BlockArgs as ImportVdjBlockArgs } from '@platforma-open/milaboratories.import-vdj.model';
import type { BlockArgs as SamplesAndDataBlockArgs } from '@platforma-open/milaboratories.samples-and-data.model';
import { blockSpec as importVdjBlockSpec } from '@platforma-open/milaboratories.import-vdj';
import { blockSpec as samplesAndDataBlockSpec } from '@platforma-open/milaboratories.samples-and-data';
import { uniquePlId, wrapOutputs } from '@platforma-sdk/model';
import { awaitStableState, blockTest } from '@platforma-sdk/test';
import { blockSpec as myBlockSpec } from 'this-block';

blockTest(
  'empty inputs',
  { timeout: 20000 },
  async ({ rawPrj: project, expect }) => {
    const blockId = await project.addBlock('Antibody Sequence Liabilities', myBlockSpec);
    const stableState = await awaitStableState(project.getBlockState(blockId), 20000);
    expect(stableState.outputs).toMatchObject({
      inputOptions: { ok: true, value: [] },
      isRunning: { ok: true, value: false },
    });
  },
);

blockTest(
  'full pipeline: SamplesAndData → ImportVDJ → AntibodySequenceLiabilities',
  { timeout: 300000 },
  async ({ rawPrj: project, helpers, expect }) => {
    const sndBlockId = await project.addBlock('Samples & Data', samplesAndDataBlockSpec);
    const importVdjBlockId = await project.addBlock('Import VDJ', importVdjBlockSpec);
    const liabilitiesBlockId = await project.addBlock('Antibody Sequence Liabilities', myBlockSpec);

    const sample1Id = uniquePlId();
    const dataset1Id = uniquePlId();

    const tsvHandle = await helpers.getLocalFileHandle('./assets/small_mixcr_data.tsv');

    // Configure SamplesAndData with a MiXCR TSV file
    await project.setBlockArgs(sndBlockId, {
      metadata: [],
      sampleIds: [sample1Id],
      sampleLabelColumnLabel: 'Sample Name',
      sampleLabels: { [sample1Id]: 'Sample 1' },
      datasets: [
        {
          id: dataset1Id,
          label: 'MiXCR Export',
          content: {
            type: 'Xsv',
            xsvType: 'tsv',
            gzipped: false,
            data: { [sample1Id]: tsvHandle },
          },
        },
      ],
      h5adFilesToPreprocess: [],
      seuratFilesToPreprocess: [],
    } satisfies SamplesAndDataBlockArgs);

    await project.runBlock(sndBlockId);
    await helpers.awaitBlockDone(sndBlockId, 30000);

    // ImportVDJ sees SamplesAndData's dataset options
    const importVdjStableState1 = await awaitStableState(
      project.getBlockState(importVdjBlockId),
      20000,
    );
    const importVdjOutputs1 = wrapOutputs(importVdjStableState1.outputs);
    expect(importVdjOutputs1.datasetOptions).toHaveLength(1);
    expect(importVdjOutputs1.datasetOptions![0].label).toBe('MiXCR Export');

    await project.setBlockArgs(importVdjBlockId, {
      datasetRef: importVdjOutputs1.datasetOptions![0].ref,
      format: 'mixcr',
      chains: ['IGHeavy', 'IGLight'],
    } satisfies ImportVdjBlockArgs);

    await project.runBlock(importVdjBlockId);
    await helpers.awaitBlockDone(importVdjBlockId, 60000);

    // AntibodySequenceLiabilities sees ImportVDJ's clonotype output
    const liabilitiesStableState1 = await awaitStableState(
      project.getBlockState(liabilitiesBlockId),
      20000,
    );
    const liabilitiesOutputs1 = wrapOutputs(liabilitiesStableState1.outputs);
    expect(liabilitiesOutputs1.inputOptions!.length).toBeGreaterThanOrEqual(1);

    await project.setBlockArgs(liabilitiesBlockId, {
      defaultBlockLabel: '',
      customBlockLabel: '',
      inputAnchor: liabilitiesOutputs1.inputOptions![0].ref,
      liabilityTypes: liabilityTypes.map((lt) => lt.value),
      customLiabilities: [],
    } satisfies BlockArgs);

    await project.runBlock(liabilitiesBlockId);
    await helpers.awaitBlockDone(liabilitiesBlockId, 120000);

    const liabilitiesStableState2 = await awaitStableState(
      project.getBlockState(liabilitiesBlockId),
      30000,
    );

    expect(liabilitiesStableState2.outputs).toMatchObject({
      isRunning: { ok: true, value: false },
      pt: { ok: true },
    });
  },
);
