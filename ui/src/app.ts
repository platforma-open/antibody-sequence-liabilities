import { platforma } from "@platforma-open/milaboratories.antibody-sequence-liabilities.model";
import { defineAppV3 } from "@platforma-sdk/ui-vue";
import { watchEffect } from "vue";
import MainPage from "./pages/MainPage.vue";

export const sdkPlugin = defineAppV3(platforma, (app) => {
  app.model.data.customBlockLabel ??= "";

  syncModality(app.model);

  return {
    routes: {
      "/": () => MainPage,
    },
  };
});

export const useApp = sdkPlugin.useApp;

type AppModel = ReturnType<typeof useApp>["model"];

function syncModality(model: AppModel) {
  watchEffect(() => {
    const modality = model.outputs.modality;
    if (modality !== undefined) {
      model.data.modality = modality;
    }
  });
}
