import React, { useState, useEffect } from 'react';
import {
  PageSection,
  Title,
  Card,
  CardBody,
  Tabs,
  Tab,
  TabTitleText,
  Grid,
  GridItem,
  Alert,
  Spinner,
  Checkbox,
  Button,
} from '@patternfly/react-core';
import { ChartLineIcon, ExternalLinkAltIcon } from '@patternfly/react-icons';

const API_BASE_URL = '/api';
const METRICS_ENDPOINT = `${API_BASE_URL}/admin/metrics`;
const DEFAULT_PROMETHEUS_PORT = '8090';

interface MetricData {
  name: string;
  value: string;
  type: string;
  help: string;
  labels?: Record<string, string>;
}

interface MetricGroup {
  [key: string]: MetricData[];
}

interface TimeSeriesData {
  timestamp: number;
  [key: string]: number;
}

interface ChartData {
  x: number;
  y: number;
  name: string;
}

export function ObservabilityPage() {
  const [activeTabKey, setActiveTabKey] = useState<string | number>(0);
  const [metrics, setMetrics] = useState<MetricGroup>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [connectionError, setConnectionError] = useState(false);
  const [timeSeriesData, setTimeSeriesData] = useState<TimeSeriesData[]>([]);
  const [isMetricSelectOpen, setIsMetricSelectOpen] = useState(false);
  const [showRate, setShowRate] = useState(false); // Toggle between raw values and rate of change
  const maxDataPoints = 60; // Keep last 60 data points (5 minutes at 5s intervals)
  
  // Load selected metrics from localStorage on mount
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('observability_selected_metrics');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.error('Failed to load selected metrics from localStorage:', e);
      return [];
    }
  });
  
  // Save selected metrics to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('observability_selected_metrics', JSON.stringify(selectedMetrics));
    } catch (e) {
      console.error('Failed to save selected metrics to localStorage:', e);
    }
  }, [selectedMetrics]);
  
  // Helper function to detect if a metric is a counter
  const isCounterMetric = (metricName: string): boolean => {
    return metricName.includes('_counter') || metricName.includes('_total');
  };
  
  // Calculate rate of change for counter metrics
  const calculateRate = (data: TimeSeriesData[], metricKey: string): number[] => {
    if (data.length < 2) return [];
    
    const rates: number[] = [];
    for (let i = 1; i < data.length; i++) {
      const currentValue = data[i][metricKey] as number;
      const prevValue = data[i - 1][metricKey] as number;
      const timeDiff = (data[i].timestamp - data[i - 1].timestamp) / 1000; // Convert to seconds
      
      if (timeDiff > 0) {
        const rate = (currentValue - prevValue) / timeDiff;
        rates.push(Math.max(0, rate)); // Ensure non-negative rates
      } else {
        rates.push(0);
      }
    }
    return rates;
  };

  const fetchMetrics = async () => {
    try {
      console.log('Fetching metrics from:', METRICS_ENDPOINT);
      
      const response = await fetch(METRICS_ENDPOINT, {
        headers: {
          'Accept': 'text/plain',
        },
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const text = await response.text();
      console.log('Received text length:', text.length);
      console.log('First 500 chars:', text.substring(0, 500));
      
      const parsed = parsePrometheusMetrics(text);
      console.log('Parsed metrics:', parsed);
      
      setMetrics(parsed);
      
      // Store time series data
      const timestamp = Date.now();
      const dataPoint: TimeSeriesData = { timestamp };
      
      // Extract numeric values from all metrics
      Object.values(parsed).flat().forEach(metric => {
        const value = parseFloat(metric.value);
        if (!isNaN(value)) {
          const key = metric.labels && Object.keys(metric.labels).length > 0
            ? `${metric.name}[${Object.entries(metric.labels).map(([k, v]) => `${k}="${v}"`).join(',')}]`
            : metric.name;
          dataPoint[key] = value;
        }
      });
      
      setTimeSeriesData(prev => {
        const newData = [...prev, dataPoint];
        // Keep only the last maxDataPoints
        return newData.slice(-maxDataPoints);
      });
      
      setError(null);
      setConnectionError(false);
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setError((err as Error).message);
      setConnectionError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    
    if (autoRefresh && !connectionError) {
      const interval = setInterval(fetchMetrics, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, connectionError]);

  const parsePrometheusMetrics = (text: string): MetricGroup => {
    const lines = text.split('\n');
    const grouped: MetricGroup = {
      skills: [],
      tools: [],
      snippets: [],
      vmcp: [],
      system: [],
    };

    let currentHelp = '';
    let currentType = '';
    let currentMetricName = '';

    for (const line of lines) {
      if (line.startsWith('#')) {
        if (line.includes('# HELP')) {
          // Format: # HELP metric_name description
          const parts = line.substring(7).trim().split(' ');
          currentMetricName = parts[0];
          currentHelp = parts.slice(1).join(' ');
        } else if (line.includes('# TYPE')) {
          // Format: # TYPE metric_name type
          const parts = line.substring(7).trim().split(' ');
          currentMetricName = parts[0];
          currentType = parts[1] || '';
        }
        continue;
      }

      if (line.trim() === '') {
        currentHelp = '';
        currentType = '';
        currentMetricName = '';
        continue;
      }

      const match = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*?)(?:\{([^}]*)\})?\s+(.+)$/);
      if (match) {
        const [, name, labelsStr, value] = match;
        
        // Filter out only _created metrics
        if (name.endsWith('_created')) {
          continue;
        }
        
        const labels: Record<string, string> = {};
        
        if (labelsStr) {
          const labelPairs = labelsStr.match(/(\w+)="([^"]*)"/g);
          if (labelPairs) {
            labelPairs.forEach(pair => {
              const [key, val] = pair.split('=');
              labels[key] = val.replace(/"/g, '');
            });
          }
        }

        const metric: MetricData = {
          name,
          value,
          type: currentType,
          help: currentHelp,
          labels,
        };

        // Categorize metrics
        if (name.startsWith('sts_fastapi_')) {
          if (name.includes('skills')) {
            grouped.skills.push(metric);
          } else if (name.includes('tools')) {
            grouped.tools.push(metric);
          } else if (name.includes('snippets')) {
            grouped.snippets.push(metric);
          } else if (name.includes('vmcp')) {
            grouped.vmcp.push(metric);
          }
        } else if (name.startsWith('sbs_fastapi_')) {
          // Also include sbs_ metrics for backward compatibility
          grouped.system.push(metric);
        } else {
          // Only include non-sts/bts metrics that are not filtered above
          grouped.system.push(metric);
        }
      }
    }

    return grouped;
  };

  const getMetricKey = (metric: MetricData): string => {
    return metric.labels && Object.keys(metric.labels).length > 0
      ? `${metric.name}[${Object.entries(metric.labels).map(([k, v]) => `${k}="${v}"`).join(',')}]`
      : metric.name;
  };

  const groupHistogramBuckets = (metrics: MetricData[]): { [key: string]: MetricData[] } => {
    const histograms: { [key: string]: MetricData[] } = {};
    
    metrics.forEach(metric => {
      if (metric.name.endsWith('_bucket')) {
        const baseName = metric.name.replace(/_bucket$/, '');
        
        // Create a unique key that includes both the base name and non-'le' labels
        // This ensures histograms with different label values are grouped separately
        const labelKey = metric.labels
          ? Object.entries(metric.labels)
              .filter(([key]) => key !== 'le')
              .map(([key, value]) => `${key}="${value}"`)
              .sort()
              .join(',')
          : '';
        
        const histogramKey = labelKey ? `${baseName}{${labelKey}}` : baseName;
        
        if (!histograms[histogramKey]) {
          histograms[histogramKey] = [];
        }
        histograms[histogramKey].push(metric);
      }
    });
    
    // Sort buckets by le (less than or equal) value
    Object.keys(histograms).forEach(histogramKey => {
      histograms[histogramKey].sort((a, b) => {
        const leA = a.labels?.le ? parseFloat(a.labels.le) : Infinity;
        const leB = b.labels?.le ? parseFloat(b.labels.le) : Infinity;
        return leA - leB;
      });
    });
    
    return histograms;
  };

  const renderHistogramCard = (histogramKey: string, buckets: MetricData[], globalMax?: number) => {
    // Extract base name and labels from the histogram key
    // Format: "base_name{label1="value1",label2="value2"}" or just "base_name"
    const match = histogramKey.match(/^([^{]+)(?:\{(.+)\})?$/);
    const baseName = match ? match[1] : histogramKey;
    const displayName = baseName.replace(/^sts_fastapi_/, '').replace(/_/g, ' ');
    
    // Prometheus histograms are cumulative, so calculate individual bucket counts
    const bucketCounts = buckets.map((bucket, index) => {
      const value = parseFloat(bucket.value);
      const prevValue = index > 0 ? parseFloat(buckets[index - 1].value) : 0;
      return value - prevValue;
    });
    
    console.log('Histogram:', histogramKey);
    console.log('Bucket counts:', bucketCounts);
    
    const localMaxBucketCount = Math.max(...bucketCounts);
    const maxBucketCount = globalMax !== undefined ? globalMax : localMaxBucketCount;
    console.log('Local max bucket count:', localMaxBucketCount);
    console.log('Using max bucket count for scaling:', maxBucketCount);
    
    // Get labels from first bucket (excluding 'le')
    const otherLabels = buckets[0].labels ?
      Object.entries(buckets[0].labels).filter(([k]) => k !== 'le') : [];
    
    return (
      <GridItem key={histogramKey} span={12}>
        <Card isCompact>
          <CardBody>
            <div style={{ marginBottom: '0.5rem' }}>
              <strong style={{ textTransform: 'capitalize' }}>{displayName} (Histogram)</strong>
            </div>
            {otherLabels.length > 0 && (
              <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem', color: '#6a6e73' }}>
                {otherLabels.map(([key, value]) => (
                  <span key={key} style={{ marginRight: '1rem' }}>
                    <strong>{key}:</strong> {value}
                  </span>
                ))}
              </div>
            )}
            <div style={{ marginTop: '1rem', paddingBottom: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', height: '200px', borderBottom: '2px solid #333' }}>
                {buckets.map((bucket, index) => {
                  const le = bucket.labels?.le || '+Inf';
                  const bucketCount = bucketCounts[index];
                  let displayHeight = 0;
                  if (bucketCount > 0 && maxBucketCount > 0) {
                    const ratio = bucketCount / maxBucketCount;
                    // Pure linear scaling - no base height to ensure proportional differences
                    displayHeight = Math.max(ratio * 180, 3); // Minimum 3px for visibility
                  }
                  
                  console.log(`Bucket ${le}: count=${bucketCount}, ratio=${bucketCount/maxBucketCount}, height=${displayHeight}px`);
                  
                  return (
                    <div key={index} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '40px' }}>
                      <div style={{ fontSize: '0.75rem', marginBottom: '0.25rem', fontWeight: 'bold', color: '#333', minHeight: '16px' }}>
                        {bucketCount > 0 ? bucketCount.toFixed(0) : ''}
                      </div>
                      <div
                        style={{
                          width: '100%',
                          height: `${displayHeight}px`,
                          backgroundColor: bucketCount > 0 ? '#06c' : 'transparent',
                          borderRadius: '2px 2px 0 0',
                          transition: 'height 0.3s ease',
                        }}
                        title={`Count: ${bucketCount.toFixed(0)}`}
                      />
                    </div>
                  );
                })}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                {buckets.map((bucket, index) => {
                  const le = bucket.labels?.le || '+Inf';
                  return (
                    <div key={index} style={{ flex: 1, fontSize: '0.75rem', color: '#6a6e73', textAlign: 'center', wordBreak: 'break-word', minWidth: '40px' }}>
                      ≤{le}
                    </div>
                  );
                })}
              </div>
            </div>
            {buckets[0].help && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#6a6e73' }}>
                {buckets[0].help}
              </div>
            )}
          </CardBody>
        </Card>
      </GridItem>
    );
  };

  const renderMetricCard = (metric: MetricData) => {
    const displayName = metric.name.replace(/^sts_fastapi_/, '').replace(/_/g, ' ');
    const hasLabels = metric.labels && Object.keys(metric.labels).length > 0;
    const metricKey = getMetricKey(metric);
    const isSelected = selectedMetrics.includes(metricKey);

    return (
      <GridItem key={`${metric.name}-${JSON.stringify(metric.labels)}`} span={6}>
        <Card
          isCompact
          isSelectable
          isSelected={isSelected}
          onClick={() => {
            setSelectedMetrics(prev =>
              prev.includes(metricKey)
                ? prev.filter(k => k !== metricKey)
                : [...prev, metricKey]
            );
          }}
          style={{ cursor: 'pointer' }}
        >
          <CardBody>
            <div style={{ marginBottom: '0.5rem' }}>
              <strong style={{ textTransform: 'capitalize' }}>{displayName}</strong>
              {isSelected && <span style={{ marginLeft: '0.5rem', color: '#06c' }}>📊</span>}
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#06c' }}>
              {parseFloat(metric.value).toFixed(2)}
            </div>
            {hasLabels && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#6a6e73' }}>
                {Object.entries(metric.labels!).map(([key, value]) => (
                  <div key={key}>
                    <strong>{key}:</strong> {value}
                  </div>
                ))}
              </div>
            )}
            {metric.help && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#6a6e73' }}>
                {metric.help}
              </div>
            )}
          </CardBody>
        </Card>
      </GridItem>
    );
  };

  const renderTimeSeriesChart = () => {
    if (selectedMetrics.length === 0) {
      return (
        <Alert variant="info" title="No metrics selected" isInline>
          Click on metric cards above to add them to the time series chart.
        </Alert>
      );
    }

    if (timeSeriesData.length < 2) {
      return (
        <Alert variant="info" title="Collecting data..." isInline>
          Time series chart will appear after collecting more data points. Currently have {timeSeriesData.length} data point(s).
        </Alert>
      );
    }

    // Prepare data for simple line chart visualization
    const colors = ['#06c', '#3e8635', '#009596', '#8461f7', '#ec7a08', '#f4c145'];
    
    // Calculate global min/max across all selected metrics for consistent Y-axis
    let dataMin = Infinity;
    let dataMax = -Infinity;
    selectedMetrics.forEach(metricKey => {
      const data = timeSeriesData.filter(d => d[metricKey] !== undefined);
      if (data.length > 0) {
        let values: number[];
        
        // Use rate values if showing rate for counter metrics
        if (showRate && isCounterMetric(metricKey)) {
          const rates = calculateRate(data, metricKey);
          if (rates.length > 0) {
            values = rates;
          } else {
            return; // Skip if no rates calculated
          }
        } else {
          values = data.map(d => d[metricKey] as number);
        }
        
        const min = Math.min(...values);
        const max = Math.max(...values);
        if (min < dataMin) dataMin = min;
        if (max > dataMax) dataMax = max;
      }
    });
    
    // Smart Y-axis scaling
    // Start from zero if:
    // 1. All values are non-negative, AND
    // 2. Either:
    //    a) The minimum value is less than 30% of the maximum (counters, rates), OR
    //    b) The data range is less than 50% of the maximum (relatively stable values)
    const dataRange = dataMax - dataMin;
    const shouldStartFromZero = dataMin >= 0 && (
      dataMin < (dataMax * 0.3) ||
      dataRange < (dataMax * 0.5)
    );
    
    const globalMin = shouldStartFromZero ? 0 : dataMin;
    const globalMax = dataMax;
    const globalRange = globalMax - globalMin || 1;
    
    // Add 5% padding to the top for better visualization
    const paddedMax = globalMax + (globalRange * 0.05);
    const paddedRange = paddedMax - globalMin;
    
    // Format timestamp for display
    const formatTime = (timestamp: number) => {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    };
    
    // Check if any selected metric is a counter
    const hasCounterMetrics = selectedMetrics.some(isCounterMetric);
    
    return (
      <div style={{ padding: '1rem', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <strong>Selected Metrics:</strong>
            {hasCounterMetrics && (
              <Checkbox
                id="show-rate"
                label="Show rate of change (for counters)"
                isChecked={showRate}
                onChange={(event, checked) => setShowRate(checked)}
              />
            )}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {selectedMetrics.map((metricKey, index) => (
              <span
                key={metricKey}
                style={{
                  padding: '0.25rem 0.5rem',
                  backgroundColor: colors[index % colors.length],
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '0.875rem',
                }}
              >
                {metricKey.replace(/^sts_fastapi_/, '').replace(/_/g, ' ')}
                {isCounterMetric(metricKey) && ' 📊'}
              </span>
            ))}
          </div>
          {hasCounterMetrics && (
            <Alert variant="info" title="Counter Metrics" isInline style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
              Counter metrics (marked with 📊) show cumulative totals by default.
              Enable "Show rate of change" to see the rate of increase per second, which better visualizes when events occur.
            </Alert>
          )}
        </div>
        
        <svg width="100%" height="350" style={{ border: '1px solid #d2d2d2', backgroundColor: 'white' }}>
          {/* Grid lines */}
          {[0, 1, 2, 3, 4].map(i => (
            <line
              key={`grid-${i}`}
              x1="70"
              y1={50 + i * 50}
              x2="95%"
              y2={50 + i * 50}
              stroke="#e0e0e0"
              strokeWidth="1"
            />
          ))}
          
          {/* Y-axis value labels */}
          {[0, 1, 2, 3, 4].map(i => {
            const value = paddedMax - (i * paddedRange / 4);
            return (
              <text
                key={`y-label-${i}`}
                x="65"
                y={50 + i * 50 + 4}
                fill="#333"
                fontSize="11"
                textAnchor="end"
              >
                {value.toFixed(2)}
              </text>
            );
          })}
          
          {/* Plot lines for each metric */}
          {selectedMetrics.map((metricKey, metricIndex) => {
            const data = timeSeriesData.filter(d => d[metricKey] !== undefined);
            if (data.length === 0) return null;
            
            // For counter metrics in rate mode, calculate rates
            let values: number[];
            let displayData: TimeSeriesData[];
            
            if (showRate && isCounterMetric(metricKey)) {
              const rates = calculateRate(data, metricKey);
              if (rates.length === 0) return null;
              
              // Create display data with rates (skip first point since we need previous value for rate)
              displayData = data.slice(1);
              values = rates;
            } else {
              displayData = data;
              values = data.map(d => d[metricKey] as number);
            }
            
            if (displayData.length === 0) return null;
            
            // Calculate points for the line using global scale with padding
            const points = displayData.map((d, i) => {
              const x = 70 + (i / (displayData.length - 1)) * (window.innerWidth * 0.82);
              const normalizedValue = (values[i] - globalMin) / paddedRange;
              const y = 250 - (normalizedValue * 200);
              return `${x},${y}`;
            }).join(' ');
            
            return (
              <g key={metricKey}>
                <polyline
                  points={points}
                  fill="none"
                  stroke={colors[metricIndex % colors.length]}
                  strokeWidth="2"
                />
                {/* Data points */}
                {displayData.map((d, i) => {
                  const x = 70 + (i / (displayData.length - 1)) * (window.innerWidth * 0.82);
                  const normalizedValue = (values[i] - globalMin) / paddedRange;
                  const y = 250 - (normalizedValue * 200);
                  const displayValue = showRate && isCounterMetric(metricKey)
                    ? `${values[i].toFixed(3)}/s`
                    : values[i].toFixed(2);
                  return (
                    <circle
                      key={i}
                      cx={x}
                      cy={y}
                      r="3"
                      fill={colors[metricIndex % colors.length]}
                    >
                      <title>{`${formatTime(d.timestamp)}: ${displayValue}`}</title>
                    </circle>
                  );
                })}
              </g>
            );
          })}
          
          {/* Axes */}
          <line x1="70" y1="50" x2="70" y2="250" stroke="#333" strokeWidth="2" />
          <line x1="70" y1="250" x2="95%" y2="250" stroke="#333" strokeWidth="2" />
          
          {/* X-axis time labels */}
          {timeSeriesData.length > 0 && [0, Math.floor(timeSeriesData.length / 2), timeSeriesData.length - 1].map((index) => {
            if (index >= timeSeriesData.length) return null;
            const x = 70 + (index / (timeSeriesData.length - 1)) * (window.innerWidth * 0.82);
            return (
              <text
                key={`x-label-${index}`}
                x={x}
                y="270"
                fill="#333"
                fontSize="11"
                textAnchor="middle"
              >
                {formatTime(timeSeriesData[index].timestamp)}
              </text>
            );
          })}
          
          {/* Axis labels */}
          <text x="25" y="150" fill="#333" fontSize="12" textAnchor="middle" transform="rotate(-90 25 150)">
            Value
          </text>
          <text x="50%" y="310" fill="#333" fontSize="12" textAnchor="middle">
            Time
          </text>
        </svg>
        
        <div style={{ marginTop: '1rem', fontSize: '0.875rem', color: '#6a6e73' }}>
          <strong>Latest Values:</strong>
          <Grid hasGutter style={{ marginTop: '0.5rem' }}>
            {selectedMetrics.map((metricKey, index) => {
              const latestData = timeSeriesData[timeSeriesData.length - 1];
              const value = latestData?.[metricKey];
              return (
                <GridItem key={metricKey} span={4}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div
                      style={{
                        width: '12px',
                        height: '12px',
                        backgroundColor: colors[index % colors.length],
                        borderRadius: '2px',
                      }}
                    />
                    <span>{metricKey.replace(/^sts_fastapi_/, '').replace(/_/g, ' ')}: </span>
                    <strong>{value !== undefined ? (value as number).toFixed(2) : 'N/A'}</strong>
                  </div>
                </GridItem>
              );
            })}
          </Grid>
        </div>
      </div>
    );
  };

  const renderMetricsGrid = (categoryMetrics: MetricData[]) => {
    if (categoryMetrics.length === 0) {
      return (
        <Alert variant="info" title="No metrics available" isInline>
          No metrics found for this category.
        </Alert>
      );
    }

    // Separate histogram buckets from regular metrics
    const histograms = groupHistogramBuckets(categoryMetrics);
    const regularMetrics = categoryMetrics.filter(m => !m.name.endsWith('_bucket'));

    console.log('Histograms found:', Object.keys(histograms));
    console.log('Regular metrics:', regularMetrics.length);

    // Calculate global max across all histograms for consistent scaling
    let globalMaxBucketCount = 0;
    Object.values(histograms).forEach(buckets => {
      const bucketCounts = buckets.map((bucket, index) => {
        const value = parseFloat(bucket.value);
        const prevValue = index > 0 ? parseFloat(buckets[index - 1].value) : 0;
        return value - prevValue;
      });
      const localMax = Math.max(...bucketCounts);
      if (localMax > globalMaxBucketCount) {
        globalMaxBucketCount = localMax;
      }
    });
    
    console.log('Global max bucket count across all histograms:', globalMaxBucketCount);

    return (
      <Grid hasGutter>
        {/* Render histograms first */}
        {Object.entries(histograms).map(([baseName, buckets]) =>
          renderHistogramCard(baseName, buckets, globalMaxBucketCount)
        )}
        {/* Then render regular metrics */}
        {regularMetrics.map(renderMetricCard)}
      </Grid>
    );
  };

  if (loading && !connectionError) {
    return (
      <PageSection>
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <Spinner size="xl" />
          <div style={{ marginTop: '1rem' }}>Loading metrics...</div>
        </div>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <Title headingLevel="h1" size="2xl">
            <ChartLineIcon style={{ marginRight: '0.5rem' }} />
            Observability
          </Title>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <Checkbox
              id="auto-refresh"
              label="Auto-refresh (5s)"
              isChecked={autoRefresh}
              onChange={(event, checked) => setAutoRefresh(checked)}
              isDisabled={connectionError}
            />
            <Button variant="primary" onClick={() => { setLoading(true); fetchMetrics(); }}>
              Refresh Now
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setTimeSeriesData([]);
                setSelectedMetrics([]);
              }}
            >
              Clear History
            </Button>
            <span style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
              {timeSeriesData.length} data points collected
            </span>
          </div>
        </div>
      </PageSection>

      {connectionError && (
        <PageSection>
          <Alert variant="danger" title="Cannot Connect to Prometheus Metrics" isInline>
            <p><strong>Error:</strong> {error}</p>
            <div style={{ marginTop: '1rem' }}>
              <p><strong>Troubleshooting Steps:</strong></p>
              <ol style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
                <li>
                  <strong>Verify the Prometheus metrics server is running</strong>
                  <ul style={{ marginLeft: '1.5rem', marginTop: '0.25rem' }}>
                    <li>The metrics endpoint should be accessible at: <code>http://localhost:{DEFAULT_PROMETHEUS_PORT}/metrics</code></li>
                    <li>Check if the service is running with observability enabled</li>
                  </ul>
                </li>
                <li>
                  <strong>Check the PROMETHEUS_METRICS_PORT environment variable</strong>
                  <ul style={{ marginLeft: '1.5rem', marginTop: '0.25rem' }}>
                    <li>Default port is {DEFAULT_PROMETHEUS_PORT}</li>
                    <li>Set via: <code>export PROMETHEUS_METRICS_PORT={DEFAULT_PROMETHEUS_PORT}</code></li>
                  </ul>
                </li>
                <li>
                  <strong>Verify the FastAPI backend is running</strong>
                  <ul style={{ marginLeft: '1.5rem', marginTop: '0.25rem' }}>
                    <li>The UI fetches metrics through the backend proxy at: <code>{METRICS_ENDPOINT}</code></li>
                    <li>Ensure the backend service is running and accessible</li>
                  </ul>
                </li>
                <li>
                  <strong>Test the endpoint manually</strong>
                  <ul style={{ marginLeft: '1.5rem', marginTop: '0.25rem' }}>
                    <li>
                      <a
                        href={`http://localhost:${DEFAULT_PROMETHEUS_PORT}/metrics`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                      >
                        Open metrics endpoint directly <ExternalLinkAltIcon />
                      </a>
                    </li>
                    <li>
                      <a
                        href={METRICS_ENDPOINT}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                      >
                        Open metrics via proxy <ExternalLinkAltIcon />
                      </a>
                    </li>
                  </ul>
                </li>
              </ol>
            </div>
            <div style={{ marginTop: '1rem' }}>
              <Button variant="primary" onClick={() => { setLoading(true); fetchMetrics(); }}>
                Retry Connection
              </Button>
            </div>
          </Alert>
        </PageSection>
      )}

      <PageSection>
        <Card>
          <CardBody>
            <Tabs
              activeKey={activeTabKey}
              onSelect={(event, tabIndex) => setActiveTabKey(tabIndex)}
              aria-label="Metrics tabs"
            >
              <Tab
                eventKey={0}
                title={<TabTitleText>Time Series</TabTitleText>}
                aria-label="Time series chart"
              >
                <div style={{ padding: '1rem' }}>
                  <Title headingLevel="h2" size="lg" style={{ marginBottom: '1rem' }}>
                    Metrics Over Time
                  </Title>
                  <Alert variant="info" title="How to use" isInline style={{ marginBottom: '1rem' }}>
                    Click on any metric card in the other tabs to add it to this time series chart.
                    Selected metrics are marked with 📊. The chart shows the last {maxDataPoints} data points (up to 5 minutes of history).
                  </Alert>
                  <Card>
                    <CardBody>
                      {renderTimeSeriesChart()}
                    </CardBody>
                  </Card>
                </div>
              </Tab>

              <Tab
                eventKey={1}
                title={<TabTitleText>Skills Metrics</TabTitleText>}
                aria-label="Skills metrics"
              >
                <div style={{ padding: '1rem' }}>
                  <Title headingLevel="h2" size="lg" style={{ marginBottom: '1rem' }}>
                    Skills API Metrics
                  </Title>
                  {renderMetricsGrid(metrics.skills || [])}
                </div>
              </Tab>

              <Tab
                eventKey={2}
                title={<TabTitleText>Tools Metrics</TabTitleText>}
                aria-label="Tools metrics"
              >
                <div style={{ padding: '1rem' }}>
                  <Title headingLevel="h2" size="lg" style={{ marginBottom: '1rem' }}>
                    Tools API Metrics
                  </Title>
                  {renderMetricsGrid(metrics.tools || [])}
                </div>
              </Tab>

              <Tab
                eventKey={3}
                title={<TabTitleText>Snippets Metrics</TabTitleText>}
                aria-label="Snippets metrics"
              >
                <div style={{ padding: '1rem' }}>
                  <Title headingLevel="h2" size="lg" style={{ marginBottom: '1rem' }}>
                    Snippets API Metrics
                  </Title>
                  {renderMetricsGrid(metrics.snippets || [])}
                </div>
              </Tab>

              <Tab
                eventKey={4}
                title={<TabTitleText>Virtual MCP Metrics</TabTitleText>}
                aria-label="Virtual MCP metrics"
              >
                <div style={{ padding: '1rem' }}>
                  <Title headingLevel="h2" size="lg" style={{ marginBottom: '1rem' }}>
                    Virtual MCP Server Metrics
                  </Title>
                  {renderMetricsGrid(metrics.vmcp || [])}
                </div>
              </Tab>

              <Tab
                eventKey={5}
                title={<TabTitleText>System Metrics</TabTitleText>}
                aria-label="System metrics"
              >
                <div style={{ padding: '1rem' }}>
                  <Title headingLevel="h2" size="lg" style={{ marginBottom: '1rem' }}>
                    System & Python Metrics
                  </Title>
                  {renderMetricsGrid(metrics.system || [])}
                </div>
              </Tab>
            </Tabs>
          </CardBody>
        </Card>
      </PageSection>
    </>
  );
}