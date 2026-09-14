// genericForm/inputs/index.ts
// Barrel exports para la carpeta inputs

export { FormattedNumberInput } from "./FormattedNumberInput";
export { InputFormattedNumber } from "./InputFormattedNumber";
export { AreaInput } from "./AreaInput";
export { InputAreaDistribution } from "./InputAreaDistribution";
export { InputCheckbox } from "./InputCheckbox";
export { InputDatePicker } from "./InputDatePicker";
export { InputFileCollection } from "./InputFileCollection";
export { InputHidden } from "./InputHidden";
export { InputImage } from "./InputImage";
export { InputNumber } from "./InputNumber";
export { InputRadio } from "./InputRadio";
export { InputSearchableSelect } from "./InputSearchableSelect";
export { InputSelectArea } from "./InputSelectArea";
export { InputSelectTipoDocumento } from "./InputSelectTipoDocumento";
export { InputSelect } from "./InputSelect";
export { InputText } from "./InputText";
export { InputTextarea } from "./InputTextarea";
export { InputDocumentoLookup } from "./InputDocumentoLookup";
export { getInputComponent, inputRegistry, registerInput } from "./registry";

export * from "./types";
