<script setup lang="ts">
import { liabilityTypes } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import type { PlRef } from '@platforma-sdk/model';
import { plRefsEqual } from '@platforma-sdk/model';
import {
  PlAgDataTableV2,
  PlBlockPage,
  PlBtnGhost,
  PlDropdownMulti,
  PlDropdownRef,
  PlEditableTitle,
  PlSlideModal,
  usePlDataTableSettingsV2,
} from '@platforma-sdk/ui-vue';
import { computed, ref, watch } from 'vue';
import { useApp } from '../app';

const app = useApp();

// Bidirectional sync between UI title and args title
watch(() => app.model.ui.title, (newTitle) => {
  app.model.args.title = newTitle;
}, { immediate: true });

// Sync args title to UI title on mount (in case args title is set but UI title isn't)
watch(() => app.model.args.title, (newTitle) => {
  if (newTitle && !app.model.ui.title) {
    app.model.ui.title = newTitle;
  }
}, { immediate: true });

function setInput(inputRef?: PlRef) {
  if (!inputRef) return;
  app.model.args.inputAnchor = inputRef;

  const label = app.model.outputs.inputOptions?.find((o) => plRefsEqual(o.ref, inputRef))?.label ?? '';

  // Set title to dataset label
  const title = 'Antibody Sequence Liabilities - ' + label;
  app.model.ui.title = title;
  app.model.args.title = title;
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

</script>

<template>
  <PlBlockPage>
    <template #title>
      <PlEditableTitle
        v-model="app.model.ui.title"
        placeholder="Antibody Sequence Liabilities"
        max-width="800px"
        :max-length="100"
        :min-length="4"
      />
    </template>
    <template #append>
      <PlBtnGhost icon="settings" @click.stop="settingsIsShown = true" />
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
    <PlDropdownMulti v-model="liabilityTypesModel" label="Liability types" :options="liabilityTypes" >
      <template #tooltip>
        Select the liability types to include in the analysis.
      </template>
    </PlDropdownMulti>
  </PlSlideModal>
</template>
