<script setup lang="ts">
import { liabilityTypes } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import type { CustomLiability } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import strings from '@milaboratories/strings';
import type { ImportFileHandle, LocalImportFileHandle, PlRef } from '@platforma-sdk/model';
import { getRawPlatformaInstance } from '@platforma-sdk/model';
import {
  PlAccordionSection,
  PlAgDataTableV2,
  PlAlert,
  PlBlockPage,
  PlBtnGhost,
  PlBtnSecondary,
  PlCheckbox,
  PlDropdown,
  PlDropdownMulti,
  PlDropdownRef,
  PlElementList,
  PlFileInput,
  PlMaskIcon24,
  PlSlideModal,
  PlTextField,
  PlTooltip,
  usePlDataTableSettingsV2,
} from '@platforma-sdk/ui-vue';
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

const predefinedSectionOpen = ref(false);

const predefinedItems = computed(() => liabilityTypes.map((lt) => ({ ...lt })));

function isLiabilityEnabled(item: (typeof liabilityTypes)[number]): boolean {
  const disabled = app.model.args.disabledPredefinedLiabilities ?? [];
  return !disabled.includes(item.value);
}

function toggleLiability(item: (typeof liabilityTypes)[number]): void {
  const disabled = app.model.args.disabledPredefinedLiabilities ?? [];
  if (disabled.includes(item.value)) {
    app.model.args.disabledPredefinedLiabilities = disabled.filter((v) => v !== item.value);
  } else {
    app.model.args.disabledPredefinedLiabilities = [...disabled, item.value];
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
  { value: 'FR4', label: 'FR4' },
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

const predefinedNameSet = new Set(liabilityTypes.map((lt) => lt.value));

function isPredefinedName(index: number): boolean {
  const name = (app.model.args.customLiabilities ?? [])[index]?.name;
  if (!name) return false;
  return predefinedNameSet.has(name);
}

function isDuplicateName(index: number): boolean {
  const items = app.model.args.customLiabilities ?? [];
  const name = items[index]?.name;
  if (!name) return false;
  return items.some((item, i) => i !== index && item.name === name);
}

function customNameError(index: number): string | undefined {
  if (isPredefinedName(index)) return 'Name collides with a predefined liability';
  if (isDuplicateName(index)) return 'Name must be unique';
  return undefined;
}

// ── Export / Import custom liabilities ───────────────────────────────────────

function exportCustomLiabilities(): void {
  const data = JSON.stringify(app.model.args.customLiabilities ?? [], null, 2);
  const blob = new Blob([data], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'custom-liabilities.json';
  a.click();
  URL.revokeObjectURL(url);
}

const importFileHandle = ref<ImportFileHandle | undefined>(undefined);
const importError = ref<string | undefined>(undefined);

watch(importFileHandle, async (handle) => {
  importError.value = undefined;
  if (!handle) return;
  let data: unknown;
  try {
    const bytes = await getRawPlatformaInstance().lsDriver.getLocalFileContent(handle as LocalImportFileHandle);
    data = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    importError.value = 'Failed to read file — ensure it is valid JSON';
    return;
  }
  if (!Array.isArray(data)) {
    importError.value = 'Invalid format: expected a JSON array';
    return;
  }
  const names = (data as CustomLiability[]).map((item) => item.name);
  if (names.length !== new Set(names).size) {
    importError.value = 'Duplicate names in imported liabilities';
    return;
  }
  const predefinedCollision = names.find((n) => predefinedNameSet.has(n));
  if (predefinedCollision) {
    importError.value = `"${predefinedCollision}" collides with a predefined liability name`;
    return;
  }
  for (const item of data as CustomLiability[]) {
    if (!item.name || !item.pattern) {
      importError.value = 'Each liability must have a name and pattern';
      return;
    }
    try {
      new RegExp(item.pattern);
    } catch {
      importError.value = `Invalid regex: "${item.pattern}"`;
      return;
    }
    if (!item.regions || item.regions.length === 0) {
      importError.value = `"${item.name}" must have at least one region`;
      return;
    }
  }
  app.model.args.customLiabilities = data as CustomLiability[];
  importFileHandle.value = undefined;
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

    <!-- Predefined liabilities section (R12): collapsible, collapsed by default -->
    <PlAccordionSection v-model="predefinedSectionOpen" label="Predefined liabilities">
      <PlCheckbox
        :model-value="app.model.args.usePredefinedLiabilities ?? true"
        @update:model-value="(v) => (app.model.args.usePredefinedLiabilities = v)"
      >
        Use predefined liabilities
      </PlCheckbox>

      <!-- Predefined list: grayed out when disabled -->
      <div
        :style="{
          opacity: (app.model.args.usePredefinedLiabilities ?? true) ? 1 : 0.4,
          pointerEvents: (app.model.args.usePredefinedLiabilities ?? true) ? 'auto' : 'none',
          transition: 'opacity 0.2s',
        }"
      >
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
              <code>{{ item.pattern }}</code> · {{ item.riskLevel }} · {{ fixabilityLabel[item.fixability] }}
            </span>
          </template>
        </PlElementList>
      </div>
    </PlAccordionSection>

    <!-- Warn when no liabilities are active (R13a) — shown outside the collapsible so always visible -->
    <PlAlert
      v-if="!app.model.args.usePredefinedLiabilities && (app.model.args.customLiabilities?.length ?? 0) === 0"
      type="warn"
    >
      No liabilities active — all sequences will pass without scoring.
    </PlAlert>

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
          :error="customNameError(index)"
        />
        <PlTextField
          v-model="customItems[index].pattern"
          label="Pattern (regex)"
          placeholder="e.g. N[GS]"
          :error="customItems[index].pattern && !isPatternValid(customItems[index].pattern) ? 'Invalid regular expression' : undefined"
        >
          <template #tooltip>
            <div>
              <code>W</code> — single character literal<br>
              <code>[GS]</code> — character class (G or S)<br>
              <code>[^P]</code> — negated class (not P)<br>
              <code>DP</code> — exact dipeptide
            </div>
          </template>
        </PlTextField>
        <PlDropdown
          v-model="customItems[index].riskLevel"
          label="Risk level"
          :options="riskLevelOptions"
        />
        <PlTooltip position="top">
          <PlDropdown
            v-model="customItems[index].fixability"
            label="Fixability"
            :options="fixabilityOptions"
          />
          <template #tooltip>
            <div>
              <b>Easy fix:</b> Single conservative substitution, minimal binding impact (e.g. Met oxidation, Trp oxidation)<br>
              <b>Fixable:</b> 1–2 mutations needed, moderate affinity risk (e.g. Deamidation N[GS], Fragmentation DP)<br>
              <b>Hard to fix:</b> Requires significant reengineering (e.g. Extra Cysteines)
            </div>
          </template>
        </PlTooltip>
        <PlDropdownMulti
          v-model="customItems[index].regions"
          label="Regions"
          :options="regionOptions"
          :error="(customItems[index].regions?.length ?? 0) === 0 ? 'At least one region must be selected' : undefined"
        />
      </template>
    </PlElementList>

    <div :style="{ display: 'flex', gap: '8px', flexWrap: 'wrap' }">
      <PlBtnSecondary icon="add" @click="addCustomLiability">
        Add custom liability
      </PlBtnSecondary>
      <PlBtnSecondary @click="exportCustomLiabilities">
        Export
      </PlBtnSecondary>
    </div>

    <!-- R16: File-picker import with SDK component + validation -->
    <PlFileInput
      v-model="importFileHandle"
      label="Import custom liabilities"
      :extensions="['json']"
      :error="importError"
      placeholder="Select JSON file"
    />
  </PlSlideModal>
</template>
