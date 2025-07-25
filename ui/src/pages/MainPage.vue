<script setup lang="ts">
import { liabilityTypes } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import type { PlRef } from '@platforma-sdk/model';
import { plRefsEqual, getRawPlatformaInstance } from '@platforma-sdk/model';
import {
  PlAgDataTableV2,
  PlBlockPage,
  PlBtnGhost,
  PlDropdownMulti,
  PlDropdownRef,
  PlSlideModal,
  usePlDataTableSettingsV2,
  PlAlert,
} from '@platforma-sdk/ui-vue';
import { asyncComputed } from '@vueuse/core';
import { computed, ref } from 'vue';
import { useApp } from '../app';

const app = useApp();

function setInput(inputRef?: PlRef) {
  if (!inputRef) return;
  app.model.args.inputAnchor = inputRef;

  const label = app.model.outputs.inputOptions?.find((o) => plRefsEqual(o.ref, inputRef))?.label ?? '';

  // Set title to dataset label
  app.model.ui.title = 'Antibody Sequence Liabilities - ' + label;
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

</script>

<template>
  <PlBlockPage>
    <template #title> Antibody sequence liabilities </template>
    <template #append>
      <PlBtnGhost icon="settings" @click.stop="settingsIsShown = true" />
    </template>
    <PlAlert v-if="isEmpty === true" type="error" style="margin-top: 1rem;">
      {{ "Error: The input dataset you have selected is empty. \
      Please choose a different dataset." }}
    </PlAlert>
    <PlAgDataTableV2
      v-model="app.model.ui.tableState"
      :settings="tableSettings"
      show-export-button
      not-ready-text="Data is not computed"
    />
  </PlBlockPage>

  <PlSlideModal v-model="settingsIsShown">
    <template #title>Settings</template>

    {{ isEmpty }}

    <PlDropdownRef
      v-model="app.model.args.inputAnchor"
      :options="app.model.outputs.inputOptions ?? []"
      label="Select dataset"
      required
      @update:model-value="setInput"
    />
    <PlDropdownMulti v-model="liabilityTypesModel" label="Liability types" :options="liabilityTypes" >
      <template #tooltip>
        Select the liability types to include in the analysis.
      </template>
    </PlDropdownMulti>
  </PlSlideModal>
</template>
