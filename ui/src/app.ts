import { getDefaultBlockLabel, liabilityTypes, model } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import { defineApp } from '@platforma-sdk/ui-vue';
import { watchEffect } from 'vue';
import MainPage from './pages/MainPage.vue';

export const sdkPlugin = defineApp(model, (app) => {
  app.model.args.customBlockLabel ??= '';

  syncDefaultBlockLabel(app.model);

  return {
    routes: {
      '/': () => MainPage,
    },
  };
});

export const useApp = sdkPlugin.useApp;

type AppModel = ReturnType<typeof useApp>['model'];

function syncDefaultBlockLabel(model: AppModel) {
  watchEffect(() => {
    model.args.defaultBlockLabel = getDefaultBlockLabel({
      liabilityTypes: model.args.liabilityTypes ?? [],
      allLiabilityTypes: liabilityTypes.map((liabilityType) => liabilityType.value),
    });
  });
}
