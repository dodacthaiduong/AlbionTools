import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { interval, Subscription } from 'rxjs';
import { switchMap, filter, take } from 'rxjs/operators';
import { ApiService, CalibrationDoc, CalibrationRect } from '../../services/api.service';
import { STEPPER_GLOBAL_OPTIONS } from '@angular/cdk/stepper';

interface CapturedRegion {
  rect: CalibrationRect;
  screenshotUrl: string | null;
  capturing: boolean;
}

@Component({
  selector: 'app-calibration',
  standalone: true,
  imports: [
    CommonModule, FormsModule, TranslateModule,
    MatStepperModule, MatButtonModule, MatInputModule,
    MatProgressSpinnerModule, MatSnackBarModule,
  ],
  providers: [{ provide: STEPPER_GLOBAL_OPTIONS, useValue: { showError: true } }],
  templateUrl: './calibration.component.html',
  styleUrl: './calibration.component.scss'
})
export class CalibrationComponent implements OnInit {
  profileName = 'default';
  rows = 8;
  cols = 6;
  saved = false;

  firstCell: CapturedRegion = { rect: { x: 0, y: 0, w: 50, h: 50 }, screenshotUrl: null, capturing: false };
  lastCell: CapturedRegion = { rect: { x: 0, y: 0, w: 50, h: 50 }, screenshotUrl: null, capturing: false };

  regionKeys: (keyof CalibrationDoc['regions'])[] = [
    'sell_now_button', 'buy_order_price', 'tooltip_item_name', 'tooltip_est_price',
    'disconnect_icon', 'popup_close', 'sort_button', 'stack_button', 'empty_slot_sample',
  ];

  regionDefaults: Record<string, { w: number; h: number }> = {
    sell_now_button:   { w: 120, h: 35 },
    buy_order_price:   { w: 150, h: 30 },
    tooltip_item_name: { w: 250, h: 25 },
    tooltip_est_price: { w: 150, h: 25 },
    disconnect_icon:   { w: 40,  h: 40 },
    popup_close:       { w: 30,  h: 30 },
    sort_button:       { w: 80,  h: 30 },
    stack_button:      { w: 80,  h: 30 },
    empty_slot_sample: { w: 10,  h: 10 },
  };

  regions: Record<string, CapturedRegion> = {};

  constructor(private api: ApiService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.regionKeys.forEach(k => {
      const d = this.regionDefaults[k];
      this.regions[k] = { rect: { x: 0, y: 0, w: d.w, h: d.h }, screenshotUrl: null, capturing: false };
    });
  }

  capture(region: CapturedRegion): void {
    region.capturing = true;
    region.screenshotUrl = null;
    this.api.startCaptureClick().subscribe(({ id }) => {
      const poll = interval(500).pipe(
        switchMap(() => this.api.pollCaptureClick(id)),
        filter(r => r.done),
        take(1),
      ).subscribe(r => {
        region.rect.x = r.x!;
        region.rect.y = r.y!;
        region.capturing = false;
        region.screenshotUrl = this.api.getScreenshotUrl(r.x!, r.y!, region.rect.w, region.rect.h);
      });
    });
  }

  refreshScreenshot(region: CapturedRegion): void {
    if (region.rect.x || region.rect.y) {
      region.screenshotUrl = this.api.getScreenshotUrl(region.rect.x, region.rect.y, region.rect.w, region.rect.h);
    }
  }

  private _computeCells(): { index: number; x: number; y: number }[] {
    const first = this.firstCell.rect;
    const last = this.lastCell.rect;
    const total = this.rows * this.cols;
    if (total <= 1) return [{ index: 0, x: first.x, y: first.y }];
    const xStep = this.cols > 1 ? (last.x - first.x) / (this.cols - 1) : 0;
    const yStep = this.rows > 1 ? (last.y - first.y) / (this.rows - 1) : 0;
    return Array.from({ length: total }, (_, i) => ({
      index: i,
      x: Math.round(first.x + (i % this.cols) * xStep),
      y: Math.round(first.y + Math.floor(i / this.cols) * yStep),
    }));
  }

  save(): void {
    const doc: CalibrationDoc = {
      profile_name: this.profileName,
      platform: 'linux-x11',
      screen: { width: window.screen.width, height: window.screen.height },
      inventory: {
        rows: this.rows,
        cols: this.cols,
        first_cell: this.firstCell.rect,
        last_cell: this.lastCell.rect,
        cells: this._computeCells(),
      },
      regions: {
        sell_now_button:   this.regions['sell_now_button'].rect,
        buy_order_price:   this.regions['buy_order_price'].rect,
        tooltip_item_name: this.regions['tooltip_item_name'].rect,
        tooltip_est_price: this.regions['tooltip_est_price'].rect,
        disconnect_icon:   this.regions['disconnect_icon'].rect,
        popup_close:       this.regions['popup_close'].rect,
        sort_button:       this.regions['sort_button'].rect,
        stack_button:      this.regions['stack_button'].rect,
        empty_slot_sample: this.regions['empty_slot_sample'].rect,
      },
    };
    this.api.saveCalibration(doc).subscribe(() => {
      this.saved = true;
      this.snack.open('Calibration saved!', undefined, { duration: 3000 });
    });
  }
}
