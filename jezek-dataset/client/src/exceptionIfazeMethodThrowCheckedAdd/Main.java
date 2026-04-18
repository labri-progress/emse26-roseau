package exceptionIfazeMethodThrowCheckedAdd;

import testing_lib.exceptionIfazeMethodThrowCheckedAdd.ExceptionIfazeMethodThrowCheckedAdd;

public class Main {

	public static void main(String[] args) {
		ExceptionIfazeMethodThrowCheckedAdd constr = new ExceptionIfazeMethodThrowCheckedAdd() {
			@Override public void method1() {}
		};
		constr.method1();
	}
	
}
