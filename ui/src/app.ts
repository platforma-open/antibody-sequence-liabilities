import { model } from '@platforma-open/milaboratories.antibody-sequence-liabilities.model';
import { defineApp } from '@platforma-sdk/ui-vue';
import { watch } from 'vue';
import MainPage from './pages/MainPage.vue';

export const sdkPlugin = defineApp(model, () => {
  return {
    routes: {
      '/': () => MainPage,
    },
  };
});

export const useApp = sdkPlugin.useApp;

// Make sure labels are initialized
const unwatch = watch(sdkPlugin, ({ loaded }) => {
  if (!loaded) return;
  const app = useApp();
  app.model.args.customBlockLabel ??= '';
  app.model.args.defaultBlockLabel ??= 'Select Dataset';
  unwatch();
});
