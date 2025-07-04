import { useEffect, useState, useRef } from "react";
import {
  Container, Typography, Button, CircularProgress, Box, Chip, Alert, Card, CardContent, Accordion, AccordionDetails, IconButton, LinearProgress, Tabs, Tab, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Modal, Fade, List, ListItem, ListItemIcon, ListItemText, CssBaseline, useMediaQuery
} from "@mui/material";
import { createTheme, ThemeProvider, useTheme } from "@mui/material/styles";
import RefreshIcon from "@mui/icons-material/Refresh";
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import CloseIcon from '@mui/icons-material/Close'; // Import CloseIcon
import axios from "axios";
import { blue, green, orange, red } from "@mui/material/colors";

// 新增：主題模式 state，預設跟隨系統
const getSystemTheme = () =>
  window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

type ProcessingStatus = 'idle' | 'updating' | 'analyzing' | 'completed' | 'error';

// 分析狀態介面
interface AnalysisStatus {
  is_running: boolean;
  current_stage: string;
  progress: number;
  message: string;
  start_time: string | null;
  end_time: string | null;
  error: string | null;
}

// 股票價格介面
interface StockPrice {
  symbol: string;
  price: number | null;
  loading: boolean;
  error: string | null;
}

// 新增：監控股票和交易歷史的介面
interface MonitoredStock {
    symbol: string;
    name: string;
    market: string;
    entry_date: string;
    entry_price: number;
    entry_composite_score: number;
    entry_confidence_score: number;
    entry_signal_conditions: string[];
    long_signal_price_at_entry: number;
}

interface TradeHistory extends MonitoredStock {
    exit_date: string;
    exit_price: number;
    profit_loss_percent: number;
    exit_reasons: string[];
}


function App() {
  const [loading, setLoading] = useState(false);
  const [watchlist, setWatchlist] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [monitoredStocks, setMonitoredStocks] = useState<MonitoredStock[]>([]);
  const [tradeHistory, setTradeHistory] = useState<TradeHistory[]>([]);
  const [lastUpdate, setLastUpdate] = useState<string>("");
  const [status, setStatus] = useState<ProcessingStatus>('idle');
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [stockPrices, setStockPrices] = useState<{ [key: string]: StockPrice }>({});
  const [themeMode, setThemeMode] = useState<'light' | 'dark'>(getSystemTheme());
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [showDetailedProgress, setShowDetailedProgress] = useState(false);
  const [currentTab, setCurrentTab] = useState(0);
  
  // 輪詢狀態的 ref
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 監聽系統主題變化
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => setThemeMode(e.matches ? 'dark' : 'light');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // 清理輪詢
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const theme = createTheme({
    palette: {
      mode: themeMode,
      ...(themeMode === 'light'
        ? {
            // 淺色模式的調色盤
            primary: { main: '#1976d2' }, // 經典藍色
            secondary: { main: '#dc004e' }, // 亮麗的粉紅色
            background: {
              default: '#f4f6f8', // 非常淺的灰色背景
              paper: '#ffffff',   // 卡片、選單等為純白色
            },
            text: {
              primary: '#333333',
              secondary: '#555555',
            },
          }
        : {
            // 深色模式的調色盤
            primary: { main: '#90caf9' }, // 淺藍色，在深色背景上更突出
            secondary: { main: '#f48fb1' }, // 柔和的粉紅色
            background: {
              default: '#121212', // 標準的深色背景
              paper: '#1e1e1e',   // 卡片、選單等為深灰色
            },
            text: {
              primary: '#e0e0e0',
              secondary: '#bdbdbd',
            },
          }),
    },
    shape: { borderRadius: 12 },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      h4: {
        fontWeight: 700,
      },
      h5: {
        fontWeight: 600,
      },
      h6: {
        fontWeight: 600,
      },
    },
    components: {
      MuiCard: {
        styleOverrides: {
          root: {
            transition: 'transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out',
            '&:hover': {
              transform: 'translateY(-4px)',
            },
          },
        },
      },
    },
  });

  // 獲取分析狀態
  const fetchAnalysisStatus = async () => {
    try {
      const response = await axios.get('/api/analysis-status');
      const status = response.data;
      setAnalysisStatus(status);
      
      // 如果分析完成，停止輪詢
      if (!status.is_running && status.current_stage === "完成") {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setStatus('completed');
        setStatusMessage("分析完成");
        setShowDetailedProgress(false);
        
        // 3秒後清除完成狀態
        setTimeout(() => {
          setStatus('idle');
          setStatusMessage("");
        }, 3000);
        
        // 重新獲取數據
        await fetchData();
      } else if (status.error) {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setStatus('error');
        setStatusMessage(`分析失敗: ${status.error}`);
        setShowDetailedProgress(false);
      }
      
    } catch (error) {
      console.error('Error fetching analysis status:', error);
    }
  };

  // 開始輪詢分析狀態
  const startStatusPolling = () => {
    // 清除現有的輪詢
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
    
    // 開始新的輪詢，每2秒檢查一次
    pollingIntervalRef.current = setInterval(fetchAnalysisStatus, 2000);
  };

  // 取得股票現價的函數
  const fetchStockPrice = async (symbol: string) => {
    try {
      console.log(`Fetching price for ${symbol}...`);
      
      // 使用後端 API 避免 CORS 問題
      const response = await axios.get(`/api/stock-price/${symbol}`, {
        timeout: 10000
      });
      
      console.log(`Response for ${symbol}:`, response.data);
      
      if (response.data?.price) {
        const price = response.data.price;
        console.log(`Price for ${symbol}: $${price}`);
        return price;
      } else {
        console.log(`No price data found for ${symbol}`);
        return null;
      }
    } catch (error) {
      console.error(`Error fetching price for ${symbol}:`, error);
      return null;
    }
  };

  // 批次取得所有股票價格
  const fetchAllStockPrices = async (symbols: string[]) => {
    try {
      // 使用後端批次 API
      const response = await axios.get('/api/stock-prices', {
        timeout: 15000
      });
      
      console.log('Batch price response:', response.data);
      
      const prices = response.data.prices || {};
      
      // 更新所有股票價格狀態
      symbols.forEach(symbol => {
        const price = prices[symbol];
        setStockPrices(prev => ({
          ...prev,
          [symbol]: { 
            symbol, 
            price, 
            loading: false, 
            error: price === null ? '無法取得價格' : null 
          }
        }));
      });
      
    } catch (error) {
      console.error('Error fetching batch prices:', error);
      
      // 如果批次 API 失敗，回退到個別 API 呼叫
      const pricePromises = symbols.map(async (symbol) => {
        // 先設定為載入狀態
        setStockPrices(prev => ({
          ...prev,
          [symbol]: { symbol, price: null, loading: true, error: null }
        }));

        const price = await fetchStockPrice(symbol);
        
        setStockPrices(prev => ({
          ...prev,
          [symbol]: { 
            symbol, 
            price, 
            loading: false, 
            error: price === null ? '無法取得價格' : null 
          }
        }));
      });

      await Promise.all(pricePromises);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    setStatus('updating');
    setStatusMessage("正在獲取最新數據...");
    
    try {
      const [w, a, monitored, history] = await Promise.all([
        axios.get("/api/watchlist"),
        axios.get("/api/analysis"),
        axios.get("/api/monitored-stocks"),
        axios.get("/api/trade-history"),
      ]);
      setWatchlist(w.data);
      setAnalysis(a.data);
      setMonitoredStocks(monitored.data);
      setTradeHistory(history.data);
      
      console.log('Analysis data:', a.data); // 調試用
      
      // 從分析結果中獲取實際的分析時間
      if (a.data?.timestamp) {
        setLastUpdate(new Date(a.data.timestamp).toLocaleString("zh-TW"));
      } else if (a.data?.analysis_date) {
        setLastUpdate(a.data.analysis_date);
      } else if (a.data?.result) {
        // 如果沒有 timestamp，使用當前時間作為備用
        setLastUpdate(new Date().toLocaleString("zh-TW"));
      }
      
      // 取得股票價格
      if (w.data?.stocks) {
        await fetchAllStockPrices(w.data.stocks);
      }
      
      setStatus('completed');
      setStatusMessage("數據更新完成");
      
      // 3秒後清除完成狀態
      setTimeout(() => {
        setStatus('idle');
        setStatusMessage("");
      }, 3000);
      
    } catch (error) {
      setStatus('error');
      setStatusMessage("獲取數據失敗");
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleManualRun = async () => {
    setLoading(true);
    setStatus('updating');
    setStatusMessage("正在觸發分析...");
    setShowDetailedProgress(true);
    
    try {
      const response = await axios.post("/api/run-now");
      
      if (response.data.status === "already_running") {
        setStatus('error');
        setStatusMessage("分析正在進行中，請稍候");
        setShowDetailedProgress(false);
        setLoading(false);
        return;
      }
      
      setStatus('analyzing');
      setStatusMessage("正在分析股票數據...");
      
      // 開始輪詢狀態
      startStatusPolling();
      
    } catch (error) {
      setStatus('error');
      setStatusMessage("觸發分析失敗");
      setShowDetailedProgress(false);
      setLoading(false);
      console.error('Error triggering analysis:', error);
    }
  };

  const getStatusColor = (status: ProcessingStatus) => {
    switch (status) {
      case 'updating': return orange[600];
      case 'analyzing': return blue[600];
      case 'completed': return green[600];
      case 'error': return red[600];
      default: return 'default';
    }
  };

  const getStatusIcon = (status: ProcessingStatus) => {
    switch (status) {
      case 'updating': return '🔄';
      case 'analyzing': return '📊';
      case 'completed': return '✅';
      case 'error': return '❌';
      default: return '';
    }
  };

  const getRankColor = (rank: number) => {
    if (rank <= 3) return '#FFD700'; // 金色
    if (rank <= 10) return '#C0C0C0'; // 銀色
    if (rank <= 20) return '#CD7F32'; // 銅色
    return '#E0E0E0'; // 灰色
  };

  const getRankIcon = (rank: number) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
  };

  // 格式化股價顯示
  const formatPrice = (symbol: string) => {
    const stockData = stockPrices[symbol];
    
    if (!stockData) {
      return '$0.00';
    }
    
    if (stockData.loading) {
      return '載入中...';
    }
    
    if (stockData.error || stockData.price === null) {
      return 'N/A';
    }
    
    return `$${stockData.price.toFixed(2)}`;
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {/* 黑暗模式切換按鈕，建議放在右上角 */}
      <Box sx={{ position: 'absolute', top: 16, right: 24, zIndex: 10 }}>
        <IconButton onClick={() => setThemeMode(themeMode === 'light' ? 'dark' : 'light')} color="inherit">
          {themeMode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
        </IconButton>
      </Box>
      <Container maxWidth={false} sx={{ pt: { xs: 8, sm: 4 }, pb: 4, px: { xs: 2, sm: 4 }, width: '100%' }}>
        <Typography variant="h4" gutterBottom fontWeight={700} sx={{ fontSize: { xs: '1.8rem', sm: '3.2rem' } }}>
          Bull Put Spread 選股神器
        </Typography>
        <Typography variant="subtitle1" gutterBottom>
          每日自動獲取美股選擇權交易量前50名，並自動分析被低估且趨勢反轉向上的股票
        </Typography>
        
        {/* 狀態顯示區域 */}
        <Box sx={{ my: 2, px: { xs: 2, sm: 3, md: 4 }, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={handleManualRun}
            disabled={loading || (analysisStatus?.is_running ?? false)}
          >
            {status === 'updating' ? '觸發分析中...' : 
             status === 'analyzing' ? '分析進行中...' : 
             analysisStatus?.is_running ? '分析進行中...' :
             '立即更新'}
          </Button>
          
          {status !== 'idle' && (
            <Chip
              label={`${getStatusIcon(status)} ${statusMessage}`}
              color={getStatusColor(status) as any}
              variant="outlined"
              size="small"
            />
          )}
          
          {lastUpdate && (
            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
              最後分析時間：{lastUpdate}
            </Typography>
          )}
        </Box>
        
        {/* 詳細進度顯示 */}
        {showDetailedProgress && analysisStatus && (
          <Box sx={{ my: 2, px: { xs: 2, sm: 3, md: 4 } }}>
            <Card elevation={2}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                  <Typography variant="h6" fontWeight="bold">
                    分析進度
                  </Typography>
                  <Chip 
                    label={`${analysisStatus.progress}%`}
                    color={analysisStatus.error ? "error" : "primary"}
                    size="small"
                  />
                </Box>
                
                <LinearProgress 
                  variant="determinate" 
                  value={analysisStatus.progress} 
                  sx={{ mb: 2, height: 8, borderRadius: 4 }}
                />
                
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="body2" fontWeight="bold" color="primary">
                    當前階段：
                  </Typography>
                  <Typography variant="body2">
                    {analysisStatus.current_stage}
                  </Typography>
                </Box>
                
                <Typography variant="body2" color="text.secondary">
                  {analysisStatus.message}
                </Typography>
                
                {analysisStatus.error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {analysisStatus.error}
                  </Alert>
                )}
                
                {analysisStatus.start_time && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                    開始時間：{new Date(analysisStatus.start_time).toLocaleString("zh-TW")}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Box>
        )}
        
        {/* 載入指示器 */}
        {loading && !showDetailedProgress && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, px: { xs: 2, sm: 3, md: 4 } }}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
              {statusMessage}
            </Typography>
          </Box>
        )}

        {/* 新增：頁籤導覽 */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', my: 3 }}>
            <Tabs value={currentTab} onChange={handleTabChange} aria-label="analysis tabs" variant="scrollable" scrollButtons="auto">
                <Tab label="分析結果摘要" />
                <Tab label={`股票監控清單 (${monitoredStocks.length})`} />
                <Tab label={`歷史交易紀錄 (${tradeHistory.length})`} />
                <Tab label="熱門股票" />
            </Tabs>
        </Box>

        {/* 頁籤內容 */}
        <Box sx={{ px: { xs: 2, sm: 3, md: 4 } }}>
            {currentTab === 0 && <AnalysisResultTab analysis={analysis} getRankColor={getRankColor} getRankIcon={getRankIcon} />}
            {currentTab === 1 && <MonitoredStocksTab stocks={monitoredStocks} />}
            {currentTab === 2 && <TradeHistoryTab trades={tradeHistory} />}
            {currentTab === 3 && <WatchlistTab watchlist={watchlist} formatPrice={formatPrice} getRankColor={getRankColor} getRankIcon={getRankIcon} />}
        </Box>

      </Container>
    </ThemeProvider>
  );
}

// 新元件：分析結果
const AnalysisResultTab = ({ analysis, getRankColor, getRankIcon }: any) => {
    const [expanded, setExpanded] = useState<string | false>(false);
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

    return (
        <>
            {/* <Typography variant="h6" sx={{ fontWeight: 'bold', fontSize: { xs: '1.5rem', sm: '1.75rem' } }}>分析結果摘要</Typography> */}
            {analysis ? (
                <Box>
                    {/* <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontSize: '14px' }}>
                        分析時間: {analysis.analysis_date || analysis.timestamp} | 
                        分析股票數: {analysis.analyzed_stocks}/{analysis.total_stocks}
                    </Typography> */}
                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr', lg: '1fr 1fr 1fr 1fr' }, gap: 2 }}>
                        {analysis.result?.filter((stock: any) => stock.status !== '無多頭訊號').map((stock: any, index: number) => (
                            <Card
                                    key={stock.symbol}
                                    elevation={2}
                                    sx={{
                                        transition: 'all 0.3s',
                                        '&:hover': { transform: 'translateY(-2px)', boxShadow: 6 },
                                        ...(isMobile && { cursor: 'pointer' }) // Add cursor pointer for mobile
                                    }}
                                    onClick={isMobile ? () => setExpanded(expanded === `panel${index}` ? false : `panel${index}`) : undefined} // Make card clickable for mobile
                                >
                                <CardContent sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1, bgcolor: 'transparent' }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                                        <Box sx={{ width: 36, height: 36, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: getRankColor(index + 1), color: index < 3 ? 'black' : 'white', fontWeight: 'bold', fontSize: '1.2rem' }}>
                                            {getRankIcon(index + 1)}
                                        </Box>
                                        <Box>
                                            <Typography variant="h5" sx={{ fontWeight: 'bold', color: 'primary.main', lineHeight: 1.2 }}>{stock.symbol}</Typography>
                                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem' }}>{stock.name}</Typography>
                                        </Box>
                                    </Box>
                                    <Box sx={{ mb: 1 }}>
                                        <Typography variant="body1" sx={{ mb: 0.8 }}>
                                            <Typography component="span" fontWeight="bold">綜合評分:</Typography> {stock.composite_score?.toFixed(1) || 'N/A'}
                                        </Typography>
                                        <Typography variant="body1" sx={{ mb: 0.8, color: stock.entry_opportunity === '強烈推薦進場' ? green[600] : stock.entry_opportunity === '建議進場' ? blue[600] : 'inherit' }}>
                                            <Typography component="span" fontWeight="bold">進場建議:</Typography> {stock.entry_opportunity || 'N/A'}
                                        </Typography>
                                        <Typography variant="body1">
                                            <Typography component="span" fontWeight="bold">信心度:</Typography> {stock.confidence_score !== undefined ? Math.round(stock.confidence_score) : 'N/A'}/100 ({stock.confidence_level})
                                        </Typography>
                                    </Box>
                                    {isMobile ? (
                                        <Accordion
                                            expanded={expanded === `panel${index}`}
                                            elevation={0}
                                            sx={{
                                                boxShadow: 'none',
                                                '&:before': { display: 'none' },
                                                mt: 1,
                                                bgcolor: 'transparent'
                                            }}
                                        >
                                            {/* Removed AccordionSummary */}
                                            {/* Custom header for mobile */}
                                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1, mb: 1 }}>
                                                {/* <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'text.secondary' }}>
                                                    詳細資訊 {expanded === `panel${index}` ? '▲' : '▼'}
                                                </Typography> */}
                                            </Box>
                                            <AccordionDetails sx={{ p: 0, display: 'flex', flexDirection: 'column', gap: 0.8, bgcolor: 'transparent' }}>
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>價格資訊</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>當前價格: ${stock.current_price?.toFixed(2)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>抄底價位: ${stock.long_signal_price?.toFixed(2)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>距離信號: {stock.distance_to_signal?.toFixed(2)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>信號後漲幅 {stock.price_change_since_signal?.toFixed(2)}%</Typography>
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>技術指標</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>RSI: {stock.rsi?.toFixed(1)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>MACD: {stock.macd?.toFixed(3)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>成交量比率: {stock.volume_ratio?.toFixed(2)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>信號信心度: {stock.long_signal_confidence?.toFixed(0)}</Typography>
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>趨勢分析</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>反轉確認: {stock.trend_reversal_confirmation?.toFixed(0)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>反轉強度: {stock.reversal_strength?.toFixed(0)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>反轉可信度: {stock.reversal_reliability?.toFixed(0)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>短期動能: {stock.short_term_momentum_turn?.toFixed(0)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>價格結構: {stock.price_structure_reversal?.toFixed(0)}%</Typography>
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>信號條件</Typography>
                                                {stock.signal_conditions?.slice(0, 5).map((cond: string, i: number) => (
                                                    <Typography variant="caption" key={i} sx={{ fontSize: '1rem' }}>• {cond}</Typography>
                                                ))}
                                                {stock.signal_conditions && stock.signal_conditions.length > 5 && (
                                                    <Typography variant="caption" sx={{ fontSize: '1rem' }}>+{stock.signal_conditions.length - 5} 更多條件</Typography>
                                                )}
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>信心因素</Typography>
                                                {stock.confidence_factors?.slice(0, 5).map((factor: string, i: number) => (
                                                    <Typography variant="caption" key={i} sx={{ fontSize: '1rem' }}>• {factor}</Typography>
                                                ))}
                                                {stock.confidence_factors && stock.confidence_factors.length > 5 && (
                                                    <Typography variant="caption" sx={{ fontSize: '1rem' }}>+{stock.confidence_factors.length - 5} 更多因素</Typography>
                                                )}
                                                <Typography variant="caption" sx={{ mt: 1, fontSize: '1rem' }}><b>信號日期:</b> {stock.latest_signal_date}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}><b>分析日期:</b> {stock.current_date}</Typography>
                                            </AccordionDetails>
                                        </Accordion>
                                    ) : (
                                        <Box sx={{ mt: 1 }}>
                                            {/* <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'text.secondary' }}>詳細資訊</Typography> */}
                                            <Box sx={{ p: 0, display: 'flex', flexDirection: 'column', gap: 0.8, bgcolor: 'transparent' }}>
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>價格資訊</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>當前價格: ${stock.current_price?.toFixed(2)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>抄底價位: ${stock.long_signal_price?.toFixed(2)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>距離信號: {stock.distance_to_signal?.toFixed(2)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>信號後漲幅 {stock.price_change_since_signal?.toFixed(2)}%</Typography>
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>技術指標</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>RSI: {stock.rsi?.toFixed(1)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>MACD: {stock.macd?.toFixed(3)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>成交量比率: {stock.volume_ratio?.toFixed(2)}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>信號信心度: {stock.long_signal_confidence?.toFixed(0)}</Typography>
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>趨勢分析</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>反轉確認: {stock.trend_reversal_confirmation?.toFixed(0)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>反轉強度: {stock.reversal_strength?.toFixed(0)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>反轉可信度: {stock.reversal_reliability?.toFixed(0)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>短期動能: {stock.short_term_momentum_turn?.toFixed(0)}%</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}>價格結構: {stock.price_structure_reversal?.toFixed(0)}%</Typography>
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>信號條件</Typography>
                                                {stock.signal_conditions?.slice(0, 5).map((cond: string, i: number) => (
                                                    <Typography variant="caption" key={i} sx={{ fontSize: '1rem' }}>• {cond}</Typography>
                                                ))}
                                                {stock.signal_conditions && stock.signal_conditions.length > 5 && (
                                                    <Typography variant="caption" sx={{ fontSize: '1rem' }}>+{stock.signal_conditions.length - 5} 更多條件</Typography>
                                                )}
                                                <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold', fontSize: '1rem' }}>信心因素</Typography>
                                                {stock.confidence_factors?.slice(0, 5).map((factor: string, i: number) => (
                                                    <Typography variant="caption" key={i} sx={{ fontSize: '1rem' }}>• {factor}</Typography>
                                                ))}
                                                {stock.confidence_factors && stock.confidence_factors.length > 5 && (
                                                    <Typography variant="caption" sx={{ fontSize: '1rem' }}>+{stock.confidence_factors.length - 5} 更多因素</Typography>
                                                )}
                                                <Typography variant="caption" sx={{ mt: 1, fontSize: '1rem' }}><b>信號日期:</b> {stock.latest_signal_date}</Typography>
                                                <Typography variant="caption" sx={{ fontSize: '1rem' }}><b>分析日期:</b> {stock.current_date}</Typography>
                                            </Box>
                                        </Box>
                                    )}
                                </CardContent>
                            </Card>
                        ))}
                    </Box>
                </Box>
            ) : <Alert severity="info">尚無分析結果，請點擊「立即更新」開始分析</Alert>}
        </>
    );
};

// 新元件：股票監控清單
const MonitoredStocksTab = ({ stocks }: { stocks: MonitoredStock[] }) => (
    <Box sx={{ overflowX: 'auto' }}>
        <TableContainer component={Paper} elevation={2}>
            <Table sx={{ minWidth: 650 }} aria-label="monitored stocks table">
                <TableHead>
                    <TableRow>
                        <TableCell sx={{ whiteSpace: 'nowrap', minWidth: '200px' }}>股票代號</TableCell>
                        <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>進場日期</TableCell>
                        <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>進場價格</TableCell>
                        <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>進場評分</TableCell>
                        <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>進場信心度</TableCell>
                        <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>抄底價位</TableCell>
                        <TableCell sx={{ whiteSpace: 'nowrap' }}>進場條件</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {(stocks ?? []).map((stock) => (
                        <TableRow key={stock.symbol} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                            <TableCell component="th" scope="row">
                                <Typography variant="subtitle2" fontWeight="bold" sx={{ fontSize: '1rem' }}>{stock.symbol}</Typography>
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '1rem' }}>{stock.name}</Typography>
                            </TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap', fontSize: '1rem' }}>{stock.entry_date}</TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap', fontSize: '1rem' }}>${stock.entry_price?.toFixed(2)}</TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap', fontSize: '1rem' }}>{stock.entry_composite_score?.toFixed(1)}</TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap', fontSize: '1rem' }}>{stock.entry_confidence_score?.toFixed(1)}</TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap', fontSize: '1rem' }}>${stock.long_signal_price_at_entry?.toFixed(2)}</TableCell>
                            <TableCell sx={{ whiteSpace: 'nowrap' }}>
                                <Tooltip title={stock.entry_signal_conditions?.join(', ')}>
                                    <Typography variant="caption" sx={{ fontSize: '1rem' }}>{(stock.entry_signal_conditions || []).slice(0, 2).join(', ')}...</Typography>
                                </Tooltip>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    </Box>
);

// 新元件：歷史交易紀錄
const TradeHistoryTab = ({ trades }: { trades: TradeHistory[] }) => {
    const [openModal, setOpenModal] = useState(false);
    const [selectedTrade, setSelectedTrade] = useState<TradeHistory | null>(null);

    const handleOpenModal = (trade: TradeHistory) => {
        setSelectedTrade(trade);
        setOpenModal(true);
    };

    const handleCloseModal = () => {
        setOpenModal(false);
        setSelectedTrade(null);
    };

    return (
        <>
            <Box sx={{ overflowX: 'auto' }}>
                <TableContainer component={Paper} elevation={2}>
                <Table sx={{ minWidth: 650 }} aria-label="trade history table">
                    <TableHead>
                        <TableRow>
                            <TableCell sx={{ whiteSpace: 'nowrap', minWidth: '200px' }}>股票代號</TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>進場日期</TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>進場價格</TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>出場日期</TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>出場價格</TableCell>
                            <TableCell align="left" sx={{ whiteSpace: 'nowrap' }}>損益</TableCell>
                            <TableCell sx={{ whiteSpace: 'nowrap' }}>出場原因</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {(trades ?? []).map((trade, index) => (
                            <TableRow key={`${trade.symbol}-${index}`} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                <TableCell component="th" scope="row">
                                    <Typography variant="subtitle2" fontWeight="bold" sx={{ fontSize: '1rem' }}>{trade.symbol}</Typography>
                                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '1rem' }}>{trade.name}</Typography>
                                </TableCell>
                                <TableCell align="left" sx={{ fontSize: '1rem' }}>{new Date(trade.entry_date).toLocaleDateString()}</TableCell>
                                <TableCell align="left" sx={{ fontSize: '1rem' }}>${trade.entry_price?.toFixed(2)}</TableCell>
                                <TableCell align="left" sx={{ fontSize: '1rem' }}>{new Date(trade.exit_date).toLocaleDateString()}</TableCell>
                                <TableCell align="left" sx={{ fontSize: '1rem' }}>${trade.exit_price?.toFixed(2)}</TableCell>
                                <TableCell align="left">
                                    <Chip 
                                        label={`${trade.profit_loss_percent?.toFixed(2)}%`}
                                        color={trade.profit_loss_percent >= 0 ? "success" : "error"}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>
                                    <Button size="small" onClick={() => handleOpenModal(trade)}>查看原因</Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
            </Box>
            <ExitReasonModal trade={selectedTrade} open={openModal} handleClose={handleCloseModal} />
        </>
    );
};

// 新元件：出場原因彈出視窗
const ExitReasonModal = ({ trade, open, handleClose }: { trade: TradeHistory | null, open: boolean, handleClose: () => void }) => {
    if (!trade) return null;

    return (
        <Modal
            open={open}
            onClose={handleClose}
            closeAfterTransition
        >
            <Fade in={open}>
                <Box sx={{
                    position: 'absolute',
                    top: { xs: 0, sm: '50%' },
                    left: { xs: 0, sm: '50%' },
                    transform: { xs: 'none', sm: 'translate(-50%, -50%)' },
                    width: { xs: '100vw', sm: 500 },
                    height: { xs: '100vh', sm: 'auto' },
                    maxWidth: { xs: '100vw', sm: '95vw' },
                    maxHeight: { xs: '100vh', sm: '90vh' },
                    bgcolor: 'background.paper',
                    borderRadius: { xs: 0, sm: 4 },
                    boxShadow: 24,
                    p: { xs: 2, sm: 3, md: 4 },
                    pb: { xs: 10, sm: 3, md: 4 }, // Add bottom padding
                    display: 'flex',
                    flexDirection: 'column'
                }}>
                    <Typography variant="h5" component="h2" fontWeight="bold" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                        <InfoOutlinedIcon color="primary" />
                        {trade.symbol} - 出場原因
                    </Typography>
                    <IconButton
                        aria-label="close"
                        onClick={handleClose}
                        sx={{
                            position: 'absolute',
                            right: 16,
                            top: 16,
                            color: (theme) => theme.palette.grey[500],
                        }}
                    >
                        <CloseIcon />
                    </IconButton>
                    <Box sx={{ overflowY: 'auto', flex: 1, my: 2 }}>
                        <List dense>
                            {trade.exit_reasons?.map((reason, index) => (
                                <ListItem key={index} sx={{ alignItems: 'flex-start' }}>
                                    <ListItemIcon sx={{ minWidth: 32, mt: 0.5 }}>
                                        <Chip label={`#${index + 1}`} size="small" />
                                    </ListItemIcon>
                                    <ListItemText 
                                        primary={reason}
                                        primaryTypographyProps={{ variant: 'body1', sx: { fontSize: '1rem' } }}
                                    />
                                </ListItem>
                            ))}
                        </List>
                    </Box>
                    
                </Box>
            </Fade>
        </Modal>
    );
};

// 新元件：原始觀察池
const WatchlistTab = ({ watchlist, formatPrice, getRankColor, getRankIcon }: any) => (
    <>
        {/* <Typography variant="h6" sx={{ fontWeight: 'bold' }}>今日選擇權交易量前50大股票</Typography> */}
        {watchlist?.stocks ? (
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)', md: 'repeat(4, 1fr)', lg: 'repeat(5, 1fr)', xl: 'repeat(6, 1fr)' }, gap: 2 }}>
                {watchlist.stocks.map((symbol: string, index: number) => (
                    <Card key={symbol} elevation={2} sx={{ height: '100%', transition: 'all 0.3s', '&:hover': { transform: 'translateY(-2px)', boxShadow: 6 } }}>
                        <CardContent sx={{ p: 2, textAlign: 'center' }}>
                            <Box sx={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 40, height: 40, borderRadius: '50%', bgcolor: getRankColor(index + 1), color: index < 3 ? 'black' : 'white', fontWeight: 'bold', mb: 1 }}>
                                {getRankIcon(index + 1)}
                            </Box>
                            <Typography variant="h6" component="div" sx={{ fontWeight: 'bold', color: 'primary.main', mb: 1, fontSize: '1rem' }}>
                                {symbol}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                {formatPrice(symbol)}
                            </Typography>
                        </CardContent>
                    </Card>
                ))}
            </Box>
        ) : <Alert severity="info">尚無股票數據，請點擊「立即更新」開始分析</Alert>}
    </>
);

export default App;