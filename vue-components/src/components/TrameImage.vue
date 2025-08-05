<script setup lang="ts">
import {
  ref,
  computed,
  useTemplateRef,
  onMounted,
  onBeforeUnmount,
  defineModel,
  withDefaults,
} from "vue";

import type { Vector2D, ViewBox } from "@/types";
import { DEFAULT_SCALE, DEFAULT_CENTER } from "@/components/defaults";

interface Props {
  src: string;
  size: Vector2D;
  borderColor?: string;
  borderSize?: number;
}

type Events = {};

const props = withDefaults(defineProps<Props>(), {
  borderColor: "white",
  borderSize: 1,
});

defineEmits<Events>();

const scale = defineModel<number>("scale", {
  required: false,
  default: DEFAULT_SCALE,
});
const center = defineModel<Vector2D>("center", {
  required: false,
  default: DEFAULT_CENTER,
});

const svgEl = useTemplateRef<SVGElement>("svg-root");

const viewPortSize = ref<Vector2D>([1, 1]);

let resizeObserver: ResizeObserver | null = null;

const viewBox = computed(() => {
  return computeViewBox(
    props.size,
    viewPortSize.value,
    scale.value,
    center.value,
  );
});
const viewBoxStr = computed(() => viewBox.value.join(" "));

const imageRatio = computed(() => props.size[0] / props.size[1]);
const viewPortRatio = computed(
  () => viewPortSize.value[0] / viewPortSize.value[1],
);
const widthRatio = computed(() => props.size[0] / viewPortSize.value[0]);
const heightRatio = computed(() => props.size[1] / viewPortSize.value[1]);
const pixelRatio = computed(() =>
  Math.max(widthRatio.value, heightRatio.value),
);

function computeViewBoxZoom(
  currentViewBox: ViewBox,
  imageSize: Vector2D,
  scale: number,
  focalPoint: Vector2D,
): ViewBox {
  const newWidth = imageSize[0] / scale;
  const newHeight = imageSize[1] / scale;

  const deltaWidth = currentViewBox[2] - newWidth;
  const deltaHeight = currentViewBox[3] - newHeight;

  return [
    currentViewBox[0] + deltaWidth * focalPoint[0],
    currentViewBox[1] + deltaHeight * focalPoint[1],
    newWidth,
    newHeight,
  ];
}

// Zoom by mouse wheel
function onWheel(ev: WheelEvent) {
  ev.stopPropagation();

  const deltaFactor = 0.2;
  const zoomIn = ev.deltaY < 0;

  let newScale: number;

  if (zoomIn) {
    newScale = scale.value * (1 + deltaFactor);
  } else {
    newScale = scale.value / (1 + deltaFactor);
  }

  const focalPoint: Vector2D = [0, 0];

  if (imageRatio.value > viewPortRatio.value) {
    focalPoint[0] = ev.offsetX / viewPortSize.value[0];
    focalPoint[1] =
      (imageRatio.value / viewPortRatio.value) *
      (ev.offsetY / viewPortSize.value[1]);
  } else {
    focalPoint[0] =
      (viewPortRatio.value / imageRatio.value) *
      (ev.offsetX / viewPortSize.value[0]);
    focalPoint[1] = ev.offsetY / viewPortSize.value[1];
  }

  const newViewBox = computeViewBoxZoom(
    viewBox.value,
    props.size,
    newScale,
    focalPoint,
  );
  const newCenter = calculateCenter(
    props.size,
    viewPortSize.value,
    [newViewBox[0], newViewBox[1]],
    newScale,
  );

  center.value = newCenter;
  scale.value = newScale;
}

// Pan by dragging the view area
function onMouseDown(ev: MouseEvent) {
  const initialPosition = [ev.clientX, ev.clientY];
  const initialOrigin: Vector2D = [viewBox.value[0], viewBox.value[1]];

  function onMouseMove(ev: MouseEvent) {
    const dx = initialPosition[0] - ev.clientX;
    const dy = initialPosition[1] - ev.clientY;

    const newOrigin: Vector2D = [
      initialOrigin[0] + (pixelRatio.value * dx) / scale.value,
      initialOrigin[1] + (pixelRatio.value * dy) / scale.value,
    ];

    center.value = calculateCenter(
      props.size,
      viewPortSize.value,
      newOrigin,
      scale.value,
    );
  }

  function onMouseUp() {
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  }

  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
}

function calculateCenter(
  imageSize: Vector2D,
  viewPortSize: Vector2D,
  origin: Vector2D,
  scale: number,
): Vector2D {
  const imageWidth = imageSize[0];
  const imageHeight = imageSize[1];
  const viewPortWidth = viewPortSize[0];
  const viewPortHeight = viewPortSize[1];
  const imageAspectRatio = imageWidth / imageHeight;
  const viewPortAspectRatio = viewPortWidth / viewPortHeight;

  const center: Vector2D = [0, 0];

  if (imageAspectRatio > viewPortAspectRatio) {
    const ratio = imageAspectRatio / viewPortAspectRatio / scale;
    center[0] = origin[0] / imageWidth + 0.5 / scale;
    center[1] = origin[1] / imageHeight + ratio / 2;
  } else {
    const ratio = viewPortAspectRatio / imageAspectRatio / scale;
    center[0] = origin[0] / imageWidth + ratio / 2;
    center[1] = origin[1] / imageHeight + 0.5 / scale;
  }

  return center;
}

function computeViewBox(
  imageSize: Vector2D,
  viewPortSize: Vector2D,
  scale: number,
  center: Vector2D,
): ViewBox {
  const imageWidth = imageSize[0];
  const imageHeight = imageSize[1];
  const viewPortWidth = viewPortSize[0];
  const viewPortHeight = viewPortSize[1];
  const imageAspectRatio = imageWidth / imageHeight;
  const viewPortAspectRatio = viewPortWidth / viewPortHeight;

  const origin: Vector2D = [0, 0];

  if (imageAspectRatio > viewPortAspectRatio) {
    const ratio = imageAspectRatio / viewPortAspectRatio / scale;
    origin[0] = -(1 / scale - 2 * center[0]) * 0.5 * imageWidth;
    origin[1] = -(ratio - 2 * center[1]) * imageHeight * 0.5;
  } else {
    const ratio = viewPortAspectRatio / imageAspectRatio / scale;
    origin[0] = -(ratio - 2 * center[0]) * imageWidth * 0.5;
    origin[1] = -(1 / scale - 2 * center[1]) * 0.5 * imageHeight;
  }

  return [origin[0], origin[1], imageWidth / scale, imageHeight / scale];
}

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    if (svgEl.value) {
      viewPortSize.value = [svgEl.value.clientWidth, svgEl.value.clientHeight];
    }
  });

  if (svgEl.value) {
    resizeObserver.observe(svgEl.value);
  }
});

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});
</script>

<template>
  <svg
    ref="svg-root"
    @wheel.prevent="onWheel"
    @mousedown="onMouseDown"
    version="1.1"
    width="100%"
    height="100%"
    xmlns="http://www.w3.org/2000/svg"
    preserveAspectRatio="xMinYMin meet"
    :viewBox="viewBoxStr"
  >
    <image
      :href="src"
      style="
        image-rendering: auto;
        image-rendering: crisp-edges;
        image-rendering: pixelated;
      "
    />
    <rect
      :width="size[0]"
      :height="size[1]"
      :stroke="borderColor"
      fill="transparent"
      :stroke-width="(borderSize * pixelRatio) / scale"
    />
    <slot
      :imageSize="size"
      :viewPortSize
      :imageRatio
      :viewPortRatio
      :widthRatio
      :heightRatio
      :pixelRatio
      :center
      :scale
      :viewBox
    ></slot>
  </svg>
</template>
