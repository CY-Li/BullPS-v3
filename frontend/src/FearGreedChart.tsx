
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Label,
} from 'recharts';
import { Card, CardContent, Typography, CircularProgress, Alert, Box } from '@mui/material';

// Define the types for the data we expect from the API
interface HistoricalData {
  date: string;
  score: number;
  rating: string;
  rating_cn: string;
}

interface CurrentIndex {
  '指數': number;
  '狀態': string;
  '更新時間': string;
  '前一日收盤': number;
  '一週前': number;
  '一月前': number;
  '一年前': number;
}

const FearGreedChart: React.FC = () => {
  const [historicalData, setHistoricalData] = useState<HistoricalData[]>([]);
  const [currentIndex, setCurrentIndex] = useState<CurrentIndex | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        // Assuming the backend is running on the same host, use a relative path
        const response = await axios.get('/api/fear-greed-index');
        const data = response.data;
        
        // Take the last 90 days of data for the chart
        const recentHistory = data.historical.slice(-90);

        setHistoricalData(recentHistory);
        setCurrentIndex(data.current);
      } catch (err) {
        console.error("Failed to fetch Fear & Greed data", err);
        setError('無法加載恐懼貪婪指數數據。請稍後再試。');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const formatXAxis = (tickItem: string) => {
    // Dates are in ISO format 'YYYY-MM-DDTHH:MM:SS'
    // We only want to show the month and day 'MM-DD'
    return new Date(tickItem).toLocaleDateString('en-CA', { month: '2-digit', day: '2-digit' });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height={400}>
        <CircularProgress />
        <Typography ml={2}>正在加載恐懼貪婪指數...</Typography>
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  const currentScore = currentIndex ? currentIndex.指數.toFixed(1) : 'N/A';
  const currentStatus = currentIndex ? currentIndex.狀態 : 'N/A';
  
  return (
    <Card sx={{ mt: 4 }}>
      <CardContent>
        <Typography variant="h5" component="div" gutterBottom>
          CNN 恐懼貪婪指數
        </Typography>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          當前指數: {currentScore} - {currentStatus}
        </Typography>
        <Box sx={{ height: 400 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={historicalData}
              margin={{
                top: 20,
                right: 30,
                left: 20,
                bottom: 20,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={formatXAxis} />
              <YAxis domain={[0, 100]} />
              <Tooltip
                formatter={(value: number) => [value.toFixed(1), '指數']}
                labelFormatter={(label: string) => new Date(label).toLocaleDateString('zh-TW')}
              />
              <Legend />

              {/* Reference Lines and Labels for different zones */}
              <ReferenceLine y={25} stroke="red" strokeDasharray="3 3">
                 <Label value="極度恐慌" position="insideTopLeft" fill="red" fontSize={12} />
              </ReferenceLine>
              <ReferenceLine y={45} stroke="orange" strokeDasharray="3 3">
                 <Label value="恐慌" position="insideTopLeft" fill="orange" fontSize={12} />
              </ReferenceLine>
              <ReferenceLine y={55} stroke="gray" strokeDasharray="3 3">
                 <Label value="中性" position="insideTopLeft" fill="gray" fontSize={12} />
              </ReferenceLine>
              <ReferenceLine y={75} stroke="green" strokeDasharray="3 3">
                 <Label value="貪婪" position="insideTopLeft" fill="green" fontSize={12} />
              </ReferenceLine>
              <ReferenceLine y={100} stroke="darkgreen" strokeDasharray="3 3">
                 <Label value="極度貪婪" position="insideTopLeft" fill="darkgreen" fontSize={12} />
              </ReferenceLine>
              
              <Line
                type="monotone"
                dataKey="score"
                name="指數"
                stroke="#8884d8"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default FearGreedChart;
