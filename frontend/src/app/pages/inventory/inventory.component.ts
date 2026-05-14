import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { MatTableModule } from '@angular/material/table';
import { ApiService, InventorySnapshot } from '../../services/api.service';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [CommonModule, TranslateModule, MatTableModule],
  templateUrl: './inventory.component.html',
  styleUrl: './inventory.component.scss'
})
export class InventoryComponent implements OnInit {
  snapshot: InventorySnapshot | null = null;
  displayedColumns = ['slot', 'full_name', 'tier', 'quantity'];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getInventory().subscribe(r => {
      this.snapshot = r.data ?? null;
    });
  }
}
