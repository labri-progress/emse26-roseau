package genericsClazzMethodTypeSwap;

import testing_lib.genericsClazzMethodTypeSwap.GenericsClazzMethodTypeSwap;

public class Main extends GenericsClazzMethodTypeSwap {

	public static void main(String[] args) {
		GenericsClazzMethodTypeSwap constr = new GenericsClazzMethodTypeSwap();
		constr.<Integer, String>method1();
	}

	@Override
	public <T, K> void method1() {

	}
}
