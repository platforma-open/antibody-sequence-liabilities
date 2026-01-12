<script setup lang="ts">
import { liabilityTypes } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import type { PlRef } from '@platforma-sdk/model';
import { getRawPlatformaInstance, plRefsEqual } from '@platforma-sdk/model';
import {
  PlAgDataTableV2,
  PlAlert,
  PlBlockPage,
  PlBtnGhost,
  PlDropdownMulti,
  PlDropdownRef,
  PlMaskIcon24,
  PlSlideModal,
  usePlDataTableSettingsV2,
} from '@platforma-sdk/ui-vue';
import { asyncComputed } from '@vueuse/core';
import { computed, ref, watchEffect } from 'vue';
import { useApp } from '../app';

const app = useApp();

function setInput(inputRef?: PlRef) {
  if (!inputRef) return;
  app.model.args.inputAnchor = inputRef;
}

const tableSettings = usePlDataTableSettingsV2({
  model: () => app.model.outputs.pt,
});

const settingsIsShown = ref(app.model.args.inputAnchor === undefined);

const liabilityTypesModel = computed({
  get: () => (app.model.args.liabilityTypes ?? []),
  set: (value) => {
    app.model.args.liabilityTypes = value ?? [];
  },
});

const isEmpty = asyncComputed(async () => {
  if (app.model.outputs.liabilitiesRiskTable === undefined) return undefined;
  return (await getRawPlatformaInstance().pFrameDriver.getShape(app.model.outputs.liabilitiesRiskTable)).rows === 0;
});

// Build defaultBlockLabel from liability types
watchEffect(() => {
  const selectedTypes = app.model.args.liabilityTypes;
  if (!selectedTypes || selectedTypes.length === 0) {
    app.model.args.defaultBlockLabel = '';
    return;
  }

  // If all liability types are selected, show "All"
  if (selectedTypes.length === liabilityTypes.length) {
    app.model.args.defaultBlockLabel = 'All';
    return;
  }

  // Build abbreviated label from selected types
  const abbreviations: Record<string, string> = {
    'Deamidation (N[GS])': 'Deam',
    'Fragmentation (DP)': 'Frag',
    'Isomerization (D[DGHST])': 'Isom',
    'N-linked Glycosylation (N[^P][ST])': 'Glyc',
    'Deamidation (N[AHNT])': 'Deam2',
    'Hydrolysis (NP)': 'Hydro',
    'Fragmentation (TS)': 'Frag2',
    'Tryptophan Oxidation (W)': 'TrpOx',
    'Methionine Oxidation (M)': 'MetOx',
    'Deamidation ([STK]N)': 'Deam3',
    'Missing Cysteines': 'MissCys',
    'Extra Cysteines': 'ExtraCys',
  };

  // PTM types
  const ptmTypes = new Set([
    'Deamidation (N[GS])',
    'Isomerization (D[DGHST])',
    'N-linked Glycosylation (N[^P][ST])',
    'Tryptophan Oxidation (W)',
    'Methionine Oxidation (M)',
  ]);

  // Fragmentation types
  const fragTypes = new Set([
    'Fragmentation (DP)',
    'Hydrolysis (NP)',
    'Fragmentation (TS)',
  ]);

  const isPTMOnly = selectedTypes.every((t) => ptmTypes.has(t)) && selectedTypes.some((t) => ptmTypes.has(t));
  const isFragOnly = selectedTypes.every((t) => fragTypes.has(t)) && selectedTypes.some((t) => fragTypes.has(t));

  if (isPTMOnly && isFragOnly) {
    app.model.args.defaultBlockLabel = 'PTM+Frag';
  } else if (isPTMOnly && selectedTypes.length === ptmTypes.size) {
    app.model.args.defaultBlockLabel = 'PTM';
  } else if (isFragOnly && selectedTypes.length === fragTypes.size) {
    app.model.args.defaultBlockLabel = 'Frag';
  } else {
    // Build label from abbreviations
    const abbrevs = selectedTypes.map((t) => abbreviations[t] || t.substring(0, 4));
    app.model.args.defaultBlockLabel = abbrevs.join('+');
  }
});

</script>

<template>
  <PlBlockPage
    v-model:subtitle="app.model.args.customBlockLabel"
    :subtitle-placeholder="app.model.args.defaultBlockLabel"
    title="Antibody Sequence Liabilities"
  >
    <template #append>
      <PlBtnGhost @click.stop="settingsIsShown = true">
        Settings
        <template #append>
          <PlMaskIcon24 name="settings" />
        </template>
      </PlBtnGhost>
    </template>
    <PlAgDataTableV2
      v-model="app.model.ui.tableState"
      :settings="tableSettings"
      show-export-button
      not-ready-text="Data is not computed"
    />
  </PlBlockPage>

  <PlSlideModal v-model="settingsIsShown">
    <template #title>Settings</template>
    <PlDropdownRef
      v-model="app.model.args.inputAnchor"
      :options="app.model.outputs.inputOptions ?? []"
      label="Select dataset"
      required
      @update:model-value="setInput"
    />
    <PlAlert v-if="isEmpty === true" type="warn" :style="{ width: '320px' }">
      <template #title>Empty dataset selection</template>
      The input dataset you have selected is empty.
      Please choose a different dataset.
    </PlAlert>
    <PlDropdownMulti v-model="liabilityTypesModel" label="Liability types" :options="liabilityTypes" >
      <template #tooltip>
        Select the liability types to include in the analysis.
      </template>
    </PlDropdownMulti>
  </PlSlideModal>
</template>
