import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function uint8ToArrayBuffer(n: number, length = 1) {
  const view = new DataView(new ArrayBuffer(length));
  view.setUint8(0, n);
  return view.buffer;
}

export function arrayBufferToUint32(buffer: ArrayBuffer) {
  var dv = new DataView(buffer, 0);
  return dv.getInt32(0, false);
};

export function arrayBufferToString(buffer: ArrayBuffer) {
  return new TextDecoder().decode(buffer);
};

export function concatArrayBuffers(buffer1: ArrayBuffer, buffer2: ArrayBuffer) {
  // 2つのArrayBufferのサイズを合計した新しいバッファを作成
  const newBuffer = new ArrayBuffer(buffer1.byteLength + buffer2.byteLength);
  const newUint8Array = new Uint8Array(newBuffer);

  // 最初のArrayBufferの内容をコピー
  newUint8Array.set(new Uint8Array(buffer1), 0);

  // 2つ目のArrayBufferの内容をコピー
  newUint8Array.set(new Uint8Array(buffer2), buffer1.byteLength);

  return newBuffer;
}