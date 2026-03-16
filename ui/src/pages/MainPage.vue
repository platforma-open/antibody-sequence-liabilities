<script setup lang="ts">
import { liabilityTypes } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import type { CustomLiability } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import strings from '@milaboratories/strings';
import type { PlRef } from '@platforma-sdk/model';
import { getRawPlatformaInstance } from '@platforma-sdk/model';
import {
  PlAgDataTableV2,
  PlAlert,
  PlBlockPage,
  PlBtnGhost,
  PlBtnSecondary,
  PlDropdown,
  PlDropdownMulti,
  PlDropdownRef,
  PlElementList,
  PlMaskIcon24,
  PlSlideModal,
  PlTextField,
  usePlDataTableSettingsV2,
} from '@platforma-sdk/ui-vue';
import { asyncComputed } from '@vueuse/core';
import { computed, ref, watch } from 'vue';
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

watch(
  () => app.model.outputs.isRunning,
  (isRunning, wasRunning) => {
    if (isRunning && !wasRunning) {
      settingsIsShown.value = false;
    }
  },
);

// ── Predefined liabilities ────────────────────────────────────────────────────

// liabilityTypes items wrapped as list items for PlElementList
const predefinedItems = computed(() => liabilityTypes.map((lt) => ({ ...lt })));

function isLiabilityEnabled(item: (typeof liabilityTypes)[number]): boolean {
  return (app.model.args.liabilityTypes ?? []).includes(item.value);
}

function toggleLiability(item: (typeof liabilityTypes)[number]): void {
  const current = app.model.args.liabilityTypes ?? [];
  if (current.includes(item.value)) {
    app.model.args.liabilityTypes = current.filter((v) => v !== item.value);
  } else {
    app.model.args.liabilityTypes = [...current, item.value];
  }
}

const fixabilityLabel: Record<string, string> = {
  easily_fixable: 'Easy fix',
  fixable: 'Fixable',
  hard_to_fix: 'Hard to fix',
  structural: 'Structural',
};

// ── Custom liabilities ────────────────────────────────────────────────────────

const regionOptions = [
  { value: 'CDR1', label: 'CDR1' },
  { value: 'CDR2', label: 'CDR2' },
  { value: 'CDR3', label: 'CDR3' },
  { value: 'FR1', label: 'FR1' },
  { value: 'FR2', label: 'FR2' },
  { value: 'FR3', label: 'FR3' },
];

const riskLevelOptions = [
  { value: 'Low', label: 'Low' },
  { value: 'Medium', label: 'Medium' },
  { value: 'High', label: 'High' },
];

const fixabilityOptions = [
  { value: 'easily_fixable', label: 'Easy fix' },
  { value: 'fixable', label: 'Fixable' },
  { value: 'hard_to_fix', label: 'Hard to fix' },
];

const customItems = computed({
  get: () => app.model.args.customLiabilities ?? [],
  set: (value) => { app.model.args.customLiabilities = value; },
});

const expandedIndices = ref<Set<number>>(new Set());

function addCustomLiability(): void {
  const current = app.model.args.customLiabilities ?? [];
  const newItem: CustomLiability = {
    name: '',
    pattern: '',
    riskLevel: 'Medium',
    fixability: 'fixable',
    regions: ['CDR1', 'CDR2', 'CDR3'],
  };
  expandedIndices.value = new Set([...expandedIndices.value, current.length]);
  app.model.args.customLiabilities = [...current, newItem];
}

function removeCustomLiability(index: number): void {
  const current = [...(app.model.args.customLiabilities ?? [])];
  current.splice(index, 1);
  const next = new Set<number>();
  for (const i of expandedIndices.value) {
    if (i < index) next.add(i);
    else if (i > index) next.add(i - 1);
  }
  expandedIndices.value = next;
  app.model.args.customLiabilities = current;
}

function toggleExpanded(index: number): void {
  const next = new Set(expandedIndices.value);
  if (next.has(index)) next.delete(index);
  else next.add(index);
  expandedIndices.value = next;
}

function isPatternValid(pattern: string): boolean {
  if (!pattern) return false;
  try {
    new RegExp(pattern);
    return true;
  } catch {
    return false;
  }
}

function isDuplicateName(index: number): boolean {
  const items = app.model.args.customLiabilities ?? [];
  const name = items[index]?.name;
  if (!name) return false;
  return items.some((item, i) => i !== index && item.name === name);
}

const isEmpty = asyncComputed(async () => {
  if (app.model.outputs.liabilitiesRiskTable === undefined) return undefined;
  return (await getRawPlatformaInstance().pFrameDriver.getShape(app.model.outputs.liabilitiesRiskTable)).rows === 0;
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
        {{ strings.titles.settings }}
        <template #append>
          <PlMaskIcon24 name="settings" />
        </template>
      </PlBtnGhost>
    </template>
    <PlAgDataTableV2
      v-model="app.model.ui.tableState"
      :settings="tableSettings"
      show-export-button
      :not-ready-text="strings.callToActions.configureSettingsAndRun"
      :no-rows-text="strings.states.noDataAvailable"
    />
  </PlBlockPage>

  <PlSlideModal v-model="settingsIsShown">
    <template #title>{{ strings.titles.settings }}</template>
    <PlDropdownRef
      v-model="app.model.args.inputAnchor"
      :options="app.model.outputs.inputOptions ?? []"
      :label="strings.titles.dataset"
      required
      @update:model-value="setInput"
    />
    <PlAlert v-if="isEmpty === true" type="warn" :style="{ width: '320px' }">
      <template #title>Empty dataset selection</template>
      The input dataset you have selected is empty.
      Please choose a different dataset.
    </PlAlert>

    <!-- Predefined liability types: toggle each on/off -->
    <PlElementList
      :items="predefinedItems"
      :get-item-key="(item) => item.value"
      :is-toggled="(item) => !isLiabilityEnabled(item)"
      :on-toggle="(item) => toggleLiability(item)"
      :is-removable="() => false"
      :disable-dragging="true"
    >
      <template #item-title="{ item }">
        {{ item.label }}
        <span :style="{ fontSize: '11px', opacity: 0.6, marginLeft: '6px' }">
          {{ item.riskLevel }} · {{ fixabilityLabel[item.fixability] }}
        </span>
      </template>
    </PlElementList>

    <!-- Custom liabilities -->
    <PlElementList
      v-model:items="customItems"
      :get-item-key="(item, index) => index"
      :is-expanded="(_item, index) => expandedIndices.has(index)"
      :on-expand="(_item, index) => toggleExpanded(index)"
      :is-removable="() => true"
      :on-remove="(_item, index) => removeCustomLiability(index)"
      :disable-dragging="true"
    >
      <template #item-title="{ item }">
        {{ item.name || 'New custom liability' }}
      </template>
      <template #item-content="{ index }">
        <PlTextField
          v-model="customItems[index].name"
          label="Name"
          placeholder="e.g. Aspartate Isomerization"
          :error="isDuplicateName(index) ? 'Name must be unique' : undefined"
        />
        <PlTextField
          v-model="customItems[index].pattern"
          label="Pattern (regex)"
          placeholder="e.g. DG"
          :error="customItems[index].pattern && !isPatternValid(customItems[index].pattern) ? 'Invalid regular expression' : undefined"
        />
        <PlDropdown
          v-model="customItems[index].riskLevel"
          label="Risk level"
          :options="riskLevelOptions"
        />
        <PlDropdown
          v-model="customItems[index].fixability"
          label="Fixability"
          :options="fixabilityOptions"
        />
        <PlDropdownMulti
          v-model="customItems[index].regions"
          label="Regions"
          :options="regionOptions"
        />
      </template>
    </PlElementList>

    <PlBtnSecondary icon="add" @click="addCustomLiability">
      Add custom liability
    </PlBtnSecondary>
  </PlSlideModal>
</template>
