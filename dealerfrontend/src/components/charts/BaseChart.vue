<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, shallowRef } from 'vue';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarController,
  BarElement,
  LineController,
  PointElement,
  LineElement,
  DoughnutController,
  PieController,
  PolarAreaController,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import type { ChartData, ChartOptions } from 'chart.js';

// Register all necessary Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarController,
  BarElement,
  LineController,
  PointElement,
  LineElement,
  DoughnutController,
  PieController,
  PolarAreaController,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const props = defineProps<{
  chartType: 'bar' | 'line' | 'doughnut' | 'pie' | 'polarArea';
  chartData: ChartData;
  chartOptions?: ChartOptions;
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
const chartInstance = shallowRef<ChartJS | null>(null);

function buildDefaultOptions(): ChartOptions {
  const defaults: ChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: '#29241E',
        titleColor: '#F4F0EA',
        bodyColor: '#F4F0EA',
        borderColor: '#DBD3C7',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        titleFont: { family: 'Inter', size: 13, weight: '600' as const },
        bodyFont: { family: 'JetBrains Mono', size: 12 },
      },
    },
    scales: undefined,
  };

  // For bar/line charts, add default scale styling
  if (props.chartType === 'bar' || props.chartType === 'line') {
    defaults.scales = {
      x: {
        grid: { display: false },
        ticks: { color: '#8C8479', font: { family: 'Inter', size: 11 } },
        border: { display: false },
      },
      y: {
        grid: { color: '#EAE4DC', drawBorder: false },
        ticks: { color: '#8C8479', font: { family: 'JetBrains Mono', size: 11 } },
        border: { display: false },
      },
    };
  }

  return defaults;
}

function mergeOptions(): ChartOptions {
  const defaults = buildDefaultOptions();
  const merged = { ...defaults, ...props.chartOptions };

  // Deep merge scales if both exist
  if (props.chartOptions?.scales && defaults.scales) {
    merged.scales = {
      ...defaults.scales,
      ...props.chartOptions.scales,
    } as ChartOptions['scales'];
  }

  // Deep merge plugins if both exist
  if (props.chartOptions?.plugins && defaults.plugins) {
    merged.plugins = {
      ...defaults.plugins,
      ...props.chartOptions.plugins,
    };
  }

  return merged;
}

function createChart(): void {
  if (!canvasRef.value) return;

  // Destroy previous instance if it exists
  if (chartInstance.value) {
    chartInstance.value.destroy();
    chartInstance.value = null;
  }

  chartInstance.value = new ChartJS(canvasRef.value, {
    type: props.chartType,
    data: props.chartData,
    options: mergeOptions(),
  });
}

onMounted(() => {
  createChart();
});

onBeforeUnmount(() => {
  if (chartInstance.value) {
    chartInstance.value.destroy();
    chartInstance.value = null;
  }
});

watch(
  () => props.chartData,
  (newData) => {
    if (chartInstance.value) {
      chartInstance.value.data = newData;
      chartInstance.value.update('none');
    }
  },
  { deep: true }
);

watch(
  () => props.chartOptions,
  () => {
    if (chartInstance.value) {
      chartInstance.value.options = mergeOptions();
      chartInstance.value.update('none');
    }
  },
  { deep: true }
);

// Recreate chart if chartType changes
watch(
  () => props.chartType,
  () => {
    createChart();
  }
);
</script>

<template>
  <div class="chart-container" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0;">
    <canvas ref="canvasRef" style="width: 100% !important; height: 100% !important;"></canvas>
  </div>
</template>
