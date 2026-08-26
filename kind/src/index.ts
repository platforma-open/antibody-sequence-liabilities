import { assertParamsObject, defineBlockKind } from "@platforma-sdk/block-kind";
import { name, version } from "../package.json" with { type: "json" };

/** How likely a liability is to be a real problem. */
export type RiskLevel = "Low" | "Medium" | "High";

/** How much work it takes to engineer a liability out. */
export type Fixability = "easily_fixable" | "fixable" | "hard_to_fix";

/**
 * A user-defined liability rule: a regex over the amino-acid sequence, plus how
 * the hit should be graded. `regions` narrows the scan to those regions; it is
 * empty in the whole-sequence modes (peptide, amplicon), which have no regions.
 *
 * Declared here because it is part of the init-params contract below. The model
 * re-exports it, so the UI keeps importing it from where it always did.
 */
export type CustomLiability = {
  name: string;
  pattern: string;
  riskLevel: RiskLevel;
  fixability: Fixability;
  regions: string[];
};

/**
 * This block's init-params contract — what a creator or a project template
 * supplies to seed a new instance. A subset of the model's `BlockData`.
 *
 * The subset is the liability panel: which predefined rules are on, which custom
 * rules to add, and which regions to scan. A team with a house liability panel
 * can pin it in a template and only pick the dataset afterwards.
 *
 * Four groups of `BlockData` fields are deliberately left out.
 *
 * - **Project-local handles.** `inputAnchor` is a `PlRef` into one project's
 *   result pool and `importFileHandle` is an `ImportFileHandle` naming a blob in
 *   one project's storage. Neither means anything in another project, so no
 *   template can carry one.
 * - **Facts about the input.** `modality` is a snapshot of a model output; it
 *   describes the dataset the user picked, so a template cannot state it in
 *   advance.
 * - **Derived state.** `defaultBlockLabel` is computed by the UI from the fields
 *   above, so carrying it would let a template contradict its own settings.
 * - **View state.** `customBlockLabel` and `tableState` exist for the UI alone.
 *
 * `mem` is left out on operator decision: the memory override is a property of
 * the machine a run happens on, not of the analysis a template describes.
 *
 * Every field is optional, because a block may be created without a template at
 * all — the model's `init` keeps its own default for each.
 */
export type BlockParams = {
  usePredefinedLiabilities?: boolean;
  disabledPredefinedLiabilities?: string[];
  customLiabilities?: CustomLiability[];
  regions?: string[];
};

const RISK_LEVELS: readonly RiskLevel[] = ["Low", "Medium", "High"];
const FIXABILITIES: readonly Fixability[] = ["easily_fixable", "fixable", "hard_to_fix"];

/**
 * The same contract at runtime, for params that arrive from a template file
 * rather than from typed code.
 *
 * Each field the contract names is read and checked here; nothing else is. A key
 * this function never reads is dropped rather than refused, so a misspelled key
 * in a template file is not caught here — it surfaces later as a block that
 * started on its defaults.
 *
 * The checks stop at the shape of a value and say nothing about whether it makes
 * sense. An empty rule name, an empty pattern, a pattern that is not a valid
 * regex, a custom rule with no region while the input is an antibody: each of
 * those is a state the settings panel can be left in, and each is refused where
 * it is used — by the UI and by the model's `args` lambda. A parser stricter than
 * the panel would make this block export a settings file its own kind then
 * refuses to apply.
 */
function parseInitializationParams(value: unknown): BlockParams {
  assertParamsObject(value);

  const { usePredefinedLiabilities, disabledPredefinedLiabilities, customLiabilities, regions } =
    value;

  return {
    usePredefinedLiabilities: optionalBoolean(usePredefinedLiabilities, "usePredefinedLiabilities"),
    disabledPredefinedLiabilities: optionalStringList(
      disabledPredefinedLiabilities,
      "disabledPredefinedLiabilities",
    ),
    customLiabilities: optionalCustomLiabilities(customLiabilities),
    regions: optionalStringList(regions, "regions"),
  };
}

function optionalBoolean(value: unknown, field: string): boolean | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "boolean") throw new Error(`'${field}' must be true or false.`);
  return value;
}

function optionalStringList(value: unknown, field: string): string[] | undefined {
  if (value === undefined) return undefined;
  if (!Array.isArray(value)) throw new Error(`'${field}' must be a list.`);
  return value.map((entry, i) => {
    if (typeof entry !== "string") throw new Error(`'${field}[${i}]' must be a string.`);
    return entry;
  });
}

function optionalEnum<T extends string>(
  value: unknown,
  allowed: readonly T[],
  field: string,
): T | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "string" || !(allowed as readonly string[]).includes(value))
    throw new Error(`'${field}' must be one of ${allowed.join(", ")}.`);
  return value as T;
}

function optionalCustomLiabilities(value: unknown): CustomLiability[] | undefined {
  if (value === undefined) return undefined;
  if (!Array.isArray(value)) throw new Error("'customLiabilities' must be a list.");
  return value.map((entry, i) => parseCustomLiability(entry, `customLiabilities[${i}]`));
}

/** Narrows a nested value the way `assertParamsObject` narrows the whole params
 *  object, but names the field it was reading — the message goes to whoever wrote
 *  the file, and "params must be an object" would point at the wrong line. */
function assertObjectAt(value: unknown, at: string): asserts value is Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    throw new Error(`'${at}' must be an object.`);
}

function parseCustomLiability(value: unknown, at: string): CustomLiability {
  assertObjectAt(value, at);

  const { name: ruleName, pattern, riskLevel, fixability, regions } = value;

  // Empty strings pass: the settings panel adds a rule with a blank name and a
  // blank pattern, and that half-filled row is ordinary state. The model's args
  // lambda is what refuses to run on it.
  if (typeof ruleName !== "string")
    throw new Error(`'${at}.name' is required, and must be a string.`);
  if (typeof pattern !== "string")
    throw new Error(`'${at}.pattern' is required, and must be a string.`);

  const parsedRisk = optionalEnum(riskLevel, RISK_LEVELS, `${at}.riskLevel`);
  if (parsedRisk === undefined) throw new Error(`'${at}.riskLevel' is required.`);
  const parsedFixability = optionalEnum(fixability, FIXABILITIES, `${at}.fixability`);
  if (parsedFixability === undefined) throw new Error(`'${at}.fixability' is required.`);

  return {
    name: ruleName,
    pattern,
    riskLevel: parsedRisk,
    fixability: parsedFixability,
    // An absent list reads as "no regions", which is what every reader of this
    // field already computes (`regions ?? []`). Filling it in here keeps the
    // returned value matching the declared type without changing its meaning.
    regions: optionalStringList(regions, `${at}.regions`) ?? [],
  };
}

// Identity (`name`/`version`) comes from this package's own `package.json`, so
// the on-wire `{name}@{version}` reference can never drift from what npm
// publishes; the bundler inlines the JSON import.
export const kind = defineBlockKind<BlockParams>({
  name,
  version,
  parseInitializationParams,
});
