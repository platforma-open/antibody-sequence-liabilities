<script setup lang="ts">
// @ts-nocheck - Disable TypeScript checking for this file
import { PlBlockPage, PlDropdownRef, PlAgDataTable, PlAgDataTableToolsPanel, PlSlideModal, PlBtnGhost, PlMaskIcon24 } from '@platforma-sdk/ui-vue';
import type { PlRef, PlDataTableSettings } from '@platforma-sdk/model';
import { plRefsEqual } from '@platforma-sdk/model';
import { computed, ref } from 'vue';
import { useApp } from '../app';

const app = useApp();

function setInput(inputRef?: PlRef) {
  if (!inputRef) return;
  app.model.args.inputAnchor = inputRef;
  app.model.args.clonotypingRunId = inputRef?.blockId;

  const title = app.model.outputs.inputOptions?.find((o) => plRefsEqual(o.ref, inputRef))?.label;

  if (inputRef.name.split('/')[1] == "abundance") {
    app.model.args.isSingleCell = true;
    app.model.args.chain = undefined;
  } else {
    app.model.args.isSingleCell = false;
    app.model.args.chain = inputRef.name.split('/')[1];
  }
                               
  // Set title to dataset label
  app.model.args.title = title;
}

const tableSettings = computed<PlDataTableSettings>(() => ({
  sourceType: 'ptable',
  pTable: app.model.outputs.pt?.table,
 // sheets: app.model.outputs.pt?.sheets,
}));

const settingsIsShown = ref(app.model.args.inputAnchor === undefined);

</script>

<template>
  <PlBlockPage>
    <template #title> Antibody sequence liabilities </template>
    <template #append>
      <PlBtnGhost @click.stop="settingsIsShown = true">
        Settings
        <template #append>
          <PlMaskIcon24 name="settings" />
        </template>
      </PlBtnGhost>
    </template>
    <PlAgDataTable v-model="app.model.ui.tableState" :settings="tableSettings" show-export-button />

    {{ app.model.args.isSingleCell }}
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

  </PlSlideModal>
</template>
