import { useEffect, useState, useRef } from "react";
import {
  Container, Typography, Button, CircularProgress, Box, Chip, Alert, Card, CardContent, Accordion, AccordionSummary, AccordionDetails, IconButton, LinearProgress
} from "@mui/material";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import RefreshIcon from "@mui/icons-material/Refresh";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
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

function App() {
  const [loading, setLoading] = useState(false);
  const [watchlist, setWatchlist] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [lastUpdate, setLastUpdate] = useState<string>("");
  const [status, setStatus] = useState<ProcessingStatus>('idle');
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [stockPrices, setStockPrices] = useState<{ [key: string]: StockPrice }>({});
  const [themeMode, setThemeMode] = useState<'light' | 'dark'>(getSystemTheme());
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [showDetailedProgress, setShowDetailedProgress] = useState(false);
  
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
      primary: { main: blue[700] },
      mode: themeMode,
    },
    shape: { borderRadius: 12 },
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
      const [w, a] = await Promise.all([
        axios.get("/api/watchlist"),
        axios.get("/api/analysis"),
      ]);
      setWatchlist(w.data);
      setAnalysis(a.data);
      
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

  return (
    <ThemeProvider theme={theme}>
      {/* 黑暗模式切換按鈕，建議放在右上角 */}
      <Box sx={{ position: 'absolute', top: 16, right: 24, zIndex: 10 }}>
        <IconButton onClick={() => setThemeMode(themeMode === 'light' ? 'dark' : 'light')} color="inherit">
          {themeMode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
        </IconButton>
      </Box>
      <Container maxWidth={false} sx={{ py: 4, px: 0, width: '100%' }}>
        <Typography variant="h4" gutterBottom fontWeight={700}>
          Bull Put Spread 選股神器
        </Typography>
        <Typography variant="subtitle1" gutterBottom>
          每日自動獲取前50大美股選擇權交易量，並自動分析被低估且趨勢反轉向上的股票
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
        
        {/* 分析結果摘要區塊 */}
        <Box sx={{ my: 3, px: { xs: 2, sm: 3, md: 4 } }}>
          <Accordion 
            defaultExpanded
            elevation={0}
            sx={{
              backgroundColor: 'transparent !important',
              '&.MuiAccordion-root': {
                boxShadow: 'none',
                borderRadius: 0,
                backgroundColor: 'transparent !important',
                '&:before': { display: 'none' },
              },
              '& .MuiAccordionSummary-root': {
                padding: 0,
                minHeight: 'auto',
              },
              '& .MuiAccordionDetails-root': {
                padding: 0,
              }
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="analysis-content"
              id="analysis-header"
            >
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                分析結果摘要
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              {analysis ? (
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontSize: '14px' }}>
                    分析時間: {analysis.analysis_date || analysis.timestamp} | 
                    分析股票數: {analysis.analyzed_stocks}/{analysis.total_stocks}
                  </Typography>
                  <Box 
                    sx={{ 
                      display: 'grid',
                      gridTemplateColumns: {
                        xs: 'repeat(1, 1fr)',
                        sm: 'repeat(2, 1fr)', 
                        md: 'repeat(3, 1fr)',
                        lg: 'repeat(4, 1fr)',
                        xl: 'repeat(5, 1fr)'
                      },
                      gap: { xs: 1, sm: 2, md: 3 }
                    }}
                  >
                    {analysis.result?.filter((stock: any) =>
                      stock.status !== '無多頭訊號'
                    ).map((stock: any, index: number) => (
                      <Card 
                        key={stock.symbol}
                        elevation={2}
                        sx={{ 
                          transition: 'all 0.3s ease',
                          '&:hover': {
                            elevation: 4,
                            transform: 'translateY(-2px)',
                            boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
                          }
                        }}
                      >
                        <CardContent sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2, bgcolor: 'background.paper', color: 'text.primary' }}>
                          {/* 排名和股票資訊 */}
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                            <Box 
                              sx={{ 
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: 32,
                                height: 32,
                                borderRadius: '50%',
                                backgroundColor: getRankColor(index + 1),
                                color: index + 1 <= 3 ? '#000' : '#fff',
                                fontWeight: 'bold',
                                fontSize: '14px',
                                mr: 1
                              }}
                            >
                              {getRankIcon(index + 1)}
                            </Box>
                            <Box>
                              <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#1976d2', fontSize: '14px' }}>
                                {stock.symbol}
                              </Typography>
                              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                                {stock.name}
                              </Typography>
                            </Box>
                          </Box>
                          
                          {/* 綜合評分 */}
                          <Box
                            sx={theme => ({
                              mb: 2,
                              p: 1,
                              borderRadius: 1,
                              bgcolor: theme.palette.mode === 'dark' ? theme.palette.background.paper : '#f5f5f5',
                              color: theme.palette.text.primary,
                            })}
                          >
                            <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '14px' }}>
                              綜合評分: {stock.composite_score?.toFixed(1) || 'N/A'}
                            </Typography>
                            <Typography variant="body2" sx={{ fontSize: '14px' }}>
                              進場建議: {stock.entry_opportunity || 'N/A'}
                            </Typography>
                            <Typography variant="body2" sx={{ fontSize: '14px' }}>
                              信心度: {stock.confidence_score !== undefined ? Math.round(stock.confidence_score) : 'N/A'}/100 ({stock.confidence_level})
                            </Typography>
                          </Box>
                          
                          {/* 價格資訊 */}
                          <Box mb={2}>
                            <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '14px' }}>
                              價格資訊
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              當前價格: ${stock.current_price?.toFixed(2) || 'N/A'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              抄底價位: ${stock.long_signal_price?.toFixed(2) || 'N/A'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              距離信號: {stock.distance_to_signal?.toFixed(2) || 'N/A'}%
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              信號後漲幅: {stock.price_change_since_signal?.toFixed(2) || 'N/A'}%
                            </Typography>
                          </Box>
                          
                          {/* 技術指標 */}
                          <Box mb={2}>
                            <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '14px' }}>
                              技術指標
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              RSI: {stock.rsi?.toFixed(1) || 'N/A'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              MACD: {stock.macd?.toFixed(3) || 'N/A'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              成交量比率: {stock.volume_ratio?.toFixed(2) || 'N/A'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              信號信心度: {stock.long_signal_confidence || 'N/A'}
                            </Typography>
                          </Box>
                          
                          {/* 趨勢分析 */}
                          <Box mb={2}>
                            <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '14px' }}>
                              趨勢分析
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              反轉確認: {stock.trend_reversal_confirmation?.toFixed(0) || 'N/A'}%
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              反轉強度: {stock.reversal_strength?.toFixed(0) || 'N/A'}%
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              反轉可信度: {stock.reversal_reliability?.toFixed(0) || 'N/A'}%
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              短期動能: {stock.short_term_momentum_turn?.toFixed(0) || 'N/A'}%
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              價格結構: {stock.price_structure_reversal?.toFixed(0) || 'N/A'}%
                            </Typography>
                          </Box>
                          
                          {/* 信號條件 */}
                          {stock.signal_conditions && stock.signal_conditions.length > 0 && (
                            <Box mb={2}>
                              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '14px' }}>
                                信號條件
                              </Typography>
                              {stock.signal_conditions.slice(0, 3).map((condition: string, idx: number) => (
                                <Typography key={idx} variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                                  • {condition}
                                </Typography>
                              ))}
                              {stock.signal_conditions.length > 3 && (
                                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px', fontStyle: 'italic' }}>
                                  +{stock.signal_conditions.length - 3} 更多條件
                                </Typography>
                              )}
                            </Box>
                          )}
                          
                          {/* 信心因素 */}
                          {stock.confidence_factors && stock.confidence_factors.length > 0 && (
                            <Box mb={2}>
                              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '14px' }}>
                                信心因素
                              </Typography>
                              {stock.confidence_factors.slice(0, 3).map((factor: string, idx: number) => (
                                <Typography key={idx} variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                                  • {factor}
                                </Typography>
                              ))}
                              {stock.confidence_factors.length > 3 && (
                                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px', fontStyle: 'italic' }}>
                                  +{stock.confidence_factors.length - 3} 更多因素
                                </Typography>
                              )}
                            </Box>
                          )}
                          
                          {/* 日期資訊 */}
                          <Box mt="auto">
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              信號日期: {stock.latest_signal_date || 'N/A'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                              分析日期: {stock.current_date || 'N/A'}
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                </Box>
              ) : (
                <Alert severity="info">
                  尚無分析結果，請點擊「立即更新」開始分析
                </Alert>
              )}
            </AccordionDetails>
          </Accordion>
        </Box>
        {/* 股票卡片區塊 */}
        <Box sx={{ my: 3, px: { xs: 2, sm: 3, md: 4 } }}>
          <Accordion 
            elevation={0}
            sx={{
              backgroundColor: 'transparent !important',
              '&.MuiAccordion-root': {
                boxShadow: 'none',
                borderRadius: 0,
                backgroundColor: 'transparent !important',
                '&:before': { display: 'none' },
              },
              '& .MuiAccordionSummary-root': {
                padding: 0,
                minHeight: 'auto',
              },
              '& .MuiAccordionDetails-root': {
                padding: 0,
              }
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="stock-cards-content"
              id="stock-cards-header"
            >
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                今日選擇權交易量前50大股票
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              {watchlist?.stocks ? (
                <Box 
                  sx={{ 
                    display: 'grid',
                    gridTemplateColumns: {
                      xs: 'repeat(2, 1fr)',
                      sm: 'repeat(3, 1fr)', 
                      md: 'repeat(4, 1fr)',
                      lg: 'repeat(5, 1fr)',
                      xl: 'repeat(6, 1fr)'
                    },
                    gap: { xs: 1, sm: 2, md: 3 }
                  }}
                >
                  {watchlist.stocks.map((symbol: string, index: number) => (
                    <Box key={symbol}>
                      <Card 
                        elevation={2}
                        sx={{ 
                          height: '100%',
                          transition: 'all 0.3s ease',
                          '&:hover': {
                            elevation: 4,
                            transform: 'translateY(-2px)',
                            boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
                          }
                        }}
                      >
                        <CardContent sx={{ p: 2, textAlign: 'center', bgcolor: 'background.paper', color: 'text.primary' }}>
                          {/* 排名徽章 */}
                          <Box 
                            sx={{ 
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              width: 40,
                              height: 40,
                              borderRadius: '50%',
                              backgroundColor: getRankColor(index + 1),
                              color: index + 1 <= 3 ? '#000' : '#fff',
                              fontWeight: 'bold',
                              fontSize: '14px',
                              mb: 1
                            }}
                          >
                            {getRankIcon(index + 1)}
                          </Box>
                          
                          {/* 股票代號 */}
                          <Typography 
                            variant="h6" 
                            component="div" 
                            sx={{ 
                              fontWeight: 'bold',
                              color: '#1976d2',
                              mb: 1,
                              fontSize: '14px'
                            }}
                          >
                            {symbol}
                          </Typography>
                          
                          {/* 股票現價 */}
                          <Typography 
                            variant="body2" 
                            color="text.secondary"
                            sx={{ fontSize: '14px' }}
                          >
                            {formatPrice(symbol)}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Alert severity="info">
                  尚無股票數據，請點擊「立即更新」開始分析
                </Alert>
              )}
            </AccordionDetails>
          </Accordion>
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;
