import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Transaction {
  id: string;
  timestamp: string;
  session_id: string;
  item: { full_name: string; tier: number; enchant: number };
  quantity: number;
  unit_price: number;
  total_price: number;
  market_city: string;
  status: string;
}

export interface ItemConfig {
  id: string;
  base_name: string;
  full_name: string;
  tier: number;
  enchant: number;
  estimated_price: number | null;
  min_sell_price: number | null;
  enabled: boolean;
  last_scanned_at: string;
}

export interface BotSession {
  id: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  stop_reason: string | null;
  stats: { cycles_completed: number; items_sold: number; total_revenue: number; errors_count: number };
}

export interface InventorySnapshot {
  id: string;
  timestamp: string;
  items: { slot: number; full_name: string; tier: number; enchant: number; quantity: number }[];
  empty_slots: number;
  total_estimated_value: number;
}

export interface CalibrationRect {
  x: number; y: number; w: number; h: number;
}

export interface CalibrationDoc {
  profile_name: string;
  platform: string;
  screen: { width: number; height: number };
  inventory: {
    rows: number; cols: number;
    first_cell: CalibrationRect;
    last_cell: CalibrationRect;
    cells: { index: number; x: number; y: number }[];
  };
  regions: {
    sell_now_button: CalibrationRect;
    buy_order_price: CalibrationRect;
    tooltip_item_name: CalibrationRect;
    tooltip_est_price: CalibrationRect;
    disconnect_icon: CalibrationRect;
    popup_close: CalibrationRect;
    sort_button: CalibrationRect;
    stack_button: CalibrationRect;
    empty_slot_sample: CalibrationRect;
  };
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = 'http://localhost:8080/api';

  constructor(private http: HttpClient) {}

  getTransactions(limit = 50, offset = 0): Observable<{ data: Transaction[]; total: number }> {
    return this.http.get<{ data: Transaction[]; total: number }>(
      `${this.base}/transactions?limit=${limit}&offset=${offset}`
    );
  }

  getExportUrl(): string {
    return `${this.base}/transactions/export`;
  }

  getItemConfigs(): Observable<{ data: ItemConfig[] }> {
    return this.http.get<{ data: ItemConfig[] }>(`${this.base}/item-configs`);
  }

  updateMinSellPrice(id: string, price: number | null): Observable<{ ok: boolean }> {
    return this.http.patch<{ ok: boolean }>(`${this.base}/item-configs/${id}`, { min_sell_price: price });
  }

  getBotStatus(): Observable<BotSession | { status: string }> {
    return this.http.get<BotSession | { status: string }>(`${this.base}/bot/status`);
  }

  getInventory(): Observable<{ data: InventorySnapshot | null }> {
    return this.http.get<{ data: InventorySnapshot | null }>(`${this.base}/inventory`);
  }

  getCalibrationProfiles(): Observable<{ data: string[] }> {
    return this.http.get<{ data: string[] }>(`${this.base}/calibration/profiles`);
  }

  startCaptureClick(): Observable<{ id: string }> {
    return this.http.post<{ id: string }>(`${this.base}/calibration/capture-click`, {});
  }

  pollCaptureClick(id: string): Observable<{ done: boolean; x?: number; y?: number }> {
    return this.http.get<{ done: boolean; x?: number; y?: number }>(`${this.base}/calibration/capture-click/${id}`);
  }

  getScreenshotUrl(x: number, y: number, w: number, h: number): string {
    return `${this.base}/calibration/screenshot?x=${x}&y=${y}&w=${w}&h=${h}`;
  }

  saveCalibration(doc: CalibrationDoc): Observable<{ id: string }> {
    return this.http.post<{ id: string }>(`${this.base}/calibration/save`, doc);
  }
}
