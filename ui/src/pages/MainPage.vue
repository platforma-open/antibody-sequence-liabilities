<script setup lang="ts">
import { liabilityTypes, predefinedLiabilityNames } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import type { CustomLiability } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import strings from '@milaboratories/strings';
import type { PlRef } from '@platforma-sdk/model';
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
  ReactiveFileContent,
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
const advancedSectionOpen = ref(false);

const predefinedItems = liabilityTypes.map((lt) => ({ ...lt }));

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

function isPredefinedName(index: number): boolean {
  const name = (app.model.args.customLiabilities ?? [])[index]?.name;
  if (!name) return false;
  return predefinedLiabilityNames.has(name);
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

const importError = ref<string | undefined>(undefined);

const reactiveFileContent = ReactiveFileContent.useGlobal();

// Used as a loading sentinel: getContentJson returns undefined for both "still loading"
// and "JSON parse failed". Watching bytes alongside data lets us tell the difference —
// bytes being defined means the file is loaded; data being undefined at that point is a parse error.
const importedFileBytes = computed(() => {
  const handle = app.model.outputs.importedFile;
  if (!handle) return undefined;
  return reactiveFileContent.getContentBytes(handle.handle).value;
});
const importedFileData = computed(() => {
  const handle = app.model.outputs.importedFile;
  if (!handle) return undefined;
  return reactiveFileContent.getContentJson(handle.handle).value;
});

watch(
  [importedFileBytes, importedFileData] as const,
  ([bytes, data]) => {
    if (bytes === undefined) return;
    if (app.model.args.importFileHandle === undefined) return;

    importError.value = undefined;

    if (data === undefined) {
      importError.value = 'Failed to read file — ensure it is valid JSON';
      app.model.args.importFileHandle = undefined;
      return;
    }
    if (!Array.isArray(data)) {
      importError.value = 'Invalid format: expected a JSON array';
      app.model.args.importFileHandle = undefined;
      return;
    }
    const names = (data as CustomLiability[]).map((item) => item.name);
    if (names.length !== new Set(names).size) {
      importError.value = 'Duplicate names in imported liabilities';
      app.model.args.importFileHandle = undefined;
      return;
    }
    const predefinedCollision = names.find((n) => predefinedLiabilityNames.has(n));
    if (predefinedCollision) {
      importError.value = `"${predefinedCollision}" collides with a predefined liability name`;
      app.model.args.importFileHandle = undefined;
      return;
    }
    for (const item of data as CustomLiability[]) {
      if (!item.name || !item.pattern) {
        importError.value = 'Each liability must have a name and pattern';
        app.model.args.importFileHandle = undefined;
        return;
      }
      try {
        new RegExp(item.pattern);
      } catch {
        importError.value = `Invalid regex: "${item.pattern}"`;
        app.model.args.importFileHandle = undefined;
        return;
      }
      if (!item.regions || item.regions.length === 0) {
        importError.value = `"${item.name}" must have at least one region`;
        app.model.args.importFileHandle = undefined;
        return;
      }
    }
    app.model.args.customLiabilities = data as CustomLiability[];
    app.model.args.importFileHandle = undefined;
  },
);
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

    <PlTooltip position="left">
      <PlCheckbox
        :model-value="app.model.args.usePredefinedLiabilities ?? true"
        @update:model-value="(v) => (app.model.args.usePredefinedLiabilities = v)"
      >
        Use predefined liabilities
      </PlCheckbox>
      <template #tooltip>
        Curated library of 13 patterns - deamidation, oxidation, fragmentation, glycosylation, and structural issues. Disable to exclude all built-in checks from scoring.
      </template>
    </PlTooltip>

    <!-- Predefined liabilities section: collapsible, collapsed by default -->
    <PlAccordionSection v-model="predefinedSectionOpen" label="Predefined liabilities">
      <!-- Predefined list: grayed out when disabled -->
      <div
        :style="{
          opacity: (app.model.args.usePredefinedLiabilities ?? true) ? 1 : 0.4,
          pointerEvents: (app.model.args.usePredefinedLiabilities ?? true) ? 'auto' : 'none',
          transition: 'opacity 0.2s',
        }"
      >
        <template v-for="item in predefinedItems" :key="item.value">
          <PlTooltip v-if="item.value === 'Integrin binding'" position="left">
            <PlCheckbox
              :model-value="isLiabilityEnabled(item)"
              @update:model-value="() => toggleLiability(item)"
            >
              {{ item.label }}
              <span :style="{ fontSize: '11px', opacity: 0.6, marginLeft: '6px' }">{{ fixabilityLabel[item.fixability] }}</span>
            </PlCheckbox>
            <template #tooltip>
              Off by default. RGD/RYD/LDV motifs trigger off-target cell adhesion via integrin receptors.
              Enable for in vivo therapeutic candidates where off-target binding is a safety concern.
            </template>
          </PlTooltip>
          <PlCheckbox
            v-else
            :model-value="isLiabilityEnabled(item)"
            @update:model-value="() => toggleLiability(item)"
          >
            {{ item.label }}
            <span :style="{ fontSize: '11px', opacity: 0.6, marginLeft: '6px' }">{{ fixabilityLabel[item.fixability] }}</span>
          </PlCheckbox>
        </template>
      </div>
    </PlAccordionSection>

    <!-- Warn when no liabilities are active — shown outside the collapsible so always visible -->
    <PlAlert
      v-if="(
        !app.model.args.usePredefinedLiabilities ||
        (app.model.args.disabledPredefinedLiabilities?.length ?? 0) >= liabilityTypes.length
      ) && (app.model.args.customLiabilities?.length ?? 0) === 0"
      type="warn"
    >
      No liabilities active — all sequences will pass without scoring.
    </PlAlert>

    <PlAccordionSection v-model="advancedSectionOpen" label="Custom liabilities">
      <!-- Custom liabilities -->
      <PlElementList
        v-model:items="customItems"
        :get-item-key="(_item, index) => index"
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
                <b>Easy fix:</b> One conservative substitution, minimal binding impact (e.g. Met oxidation, Trp oxidation)<br>
                <b>Fixable:</b> 1–2 mutations, moderate affinity risk (e.g. Deamidation N[GS], Fragmentation DP)<br>
                <b>Hard to fix:</b> Significant reengineering required (e.g. Extra Cysteines)
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

      <PlBtnSecondary icon="add" :style="{ width: '100%' }" @click="addCustomLiability">
        Add custom liability
      </PlBtnSecondary>
      <PlBtnSecondary :style="{ width: '100%' }" @click="exportCustomLiabilities">
        Export custom liabilities
      </PlBtnSecondary>
      <PlTooltip position="top">
        <PlFileInput
          v-model="app.model.args.importFileHandle"
          label="Import custom liabilities"
          :extensions="['json']"
          :error="importError"
          placeholder="Select JSON file"
        />
        <template #tooltip>
          Importing replaces your current custom liabilities.
        </template>
      </PlTooltip>
    </PlAccordionSection>
  </PlSlideModal>
</template>
